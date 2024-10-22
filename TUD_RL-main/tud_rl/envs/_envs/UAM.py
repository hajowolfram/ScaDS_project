import random
from copy import copy
from string import ascii_letters
from typing import List

import gym
from bluesky.tools.geo import latlondist, qdrdist, qdrpos
from gym import spaces
from matplotlib import pyplot as plt
from mycolorpy import colorlist as mcp

from tud_rl.agents.base import _Agent
from tud_rl.envs._envs.HHOS_Fnc import to_utm
from tud_rl.envs._envs.Plane import *
from tud_rl.envs._envs.VesselFnc import (NM_to_meter, angle_to_2pi,
                                         angle_to_pi, dtr, meter_to_NM)

COLORS = [plt.rcParams["axes.prop_cycle"].by_key()["color"][i] for i in range(8)] + 5 * mcp.gen_color(cmap="tab20b", n=20) 


class Destination:
    def __init__(self, dt) -> None:
        # size
        self.radius = 100          # [m]
        self.spawn_radius   = 1100 # [m]
        self.respawn_radius = 1300 # [m]
        
        # position
        self.lat = 10  # [deg]
        self.lon = 10  # [deg]
        self.N, self.E, _ = to_utm(self.lat, self.lon) # [m], [m]

        # timing
        self.dt = dt             # [s], simulation time step
        self._t_close = 60       # [s], time the destination is closed after an aircraft has entered 
        self._t_nxt_open = 0     # [s], current time until the destination opens again
        self._t_open_since = 0   # [s], current time since the vertiport is open
        self._was_open = True
        self.open()

    def reset(self):
        self.open()

    def step(self, planes: List[Plane]):
        """Updates status of the destination.
        Returns:
            np.ndarray([number_of_planes,]): who entered a closed destination
            np.ndarray([number_of_planes,]): who entered an open destination"""
        # count time until next opening
        if self._is_open is False:
            self._t_nxt_open -= self.dt
            if self._t_nxt_open <= 0:
                self.open()
        else:
            self._t_open_since += self.dt

        # store opening status
        self._was_open = copy(self._is_open)

        # check who entered a closed or open destination
        entered_close = np.zeros(len(planes), dtype=bool)
        entered_open  = np.zeros(len(planes), dtype=bool)

        for i, p in enumerate(planes):
            if p.D_dest <= self.radius:            
                if self._is_open:
                    entered_open[i] = True
                else:
                    entered_close[i] = True

        #  close if someone entered
        if any(entered_open):
            self.close()

        return entered_close, entered_open

    def open(self):
        self._t_open_since = 0
        self._t_nxt_open = 0
        self._is_open = True
        self.color = "green"
    
    def close(self):
        self._t_open_since = 0
        self._is_open = False
        self._t_nxt_open = copy(self._t_close)
        self.color = "red"

    @property
    def t_nxt_open(self):
        return self._t_nxt_open

    @property
    def t_close(self):
        return self._t_close

    @property
    def t_open_since(self):
        return self._t_open_since

    @property
    def is_open(self):
        return self._is_open

    @property
    def was_open(self):
        return self._was_open


class UAM(gym.Env):
    """Urban air mobility simulation env based on the BlueSky simulator of Ellerbroek and Hoekstra.
    Note: If multi_policy is True, each plane is considered an agent. Otherwise, the first plane operates as a single agent."""
    def __init__(self, 
                 N_agents_max :int, 
                 multi_policy :bool, 
                 prio:bool,
                 full_RL:bool, 
                 w_coll:float, 
                 w_goal:float):
        super(UAM, self).__init__()

        # setup
        self.N_agents_max = N_agents_max
        assert N_agents_max > 1, "Need at least two aircrafts."

        self.multi_policy = multi_policy
        self.prio = prio

        self.acalt = 300 # [m]
        self.actas = 15  # [m/s]
        self.actype = "MAVIC"

        if not multi_policy:
            self.history_length = 2

        self.full_RL = full_RL
        self.w_coll  = w_coll
        self.w_goal  = w_goal
        self.w = self.w_coll + self.w_goal

        # domain params
        self.incident_dist = 100 # [m]
        self.accident_dist = 10  # [m]
        self.clock_degs = np.linspace(0.0, 360.0, num=100, endpoint=True)

        # destination
        self.dt = 1.0
        self.dest = Destination(self.dt)

        # performance model
        self.perf = OpenAP(self.actype, self.actas, self.acalt)

        # config
        self.OS_obs     = 5 if prio else 4
        self.obs_per_TS = 5 if prio else 4
        self.obs_size   = self.OS_obs + self.obs_per_TS*(self.N_agents_max-1)

        self.observation_space = spaces.Box(low  = np.full(self.obs_size, -np.inf, dtype=np.float32), 
                                            high = np.full(self.obs_size,  np.inf, dtype=np.float32))
        self.act_size = 1
        self.action_space = spaces.Box(low  = np.full(self.act_size, -1.0, dtype=np.float32), 
                                        high = np.full(self.act_size, +1.0, dtype=np.float32))
        self._max_episode_steps = 500

        # viz
        self.plot_reward = True
        self.plot_state  = True

        atts = ["D_TS", "bng_TS", "V_R", "C_T", "next"]

        other_names = []
        for i in range(self.N_agents_max-1):
            others = [ele + ascii_letters[i] for ele in atts]
            other_names += others

        self.obs_names = ["bng_goal", "D_goal", "next", "t_close", "t_open"] + other_names

    def reset(self):
        """Resets environment to initial state."""
        self.step_cnt = 0           # simulation step counter
        self.sim_t    = 0           # overall passed simulation time (in s)

        self.N_accs = 0   # number of accidents during episode
        self.N_incs = 0   # number of incidents during episode
        self.N_enterances_closed_d = 0   # number of enterances to the vertiport although it was closed

        # create some aircrafts
        self.planes:List[Plane] = []

        if self.multi_policy:
            self.N_planes = self.N_agents_max
        else:
            self.N_planes = np.random.choice([2, 4, 6, 8, 10])

        for n in range(self.N_planes):
            self.planes.append(self._spawn_plane(n, random=bool(random.getrandbits(1))))

        # init live times
        if self.prio:
            self.ts_alive = np.array(random.sample(population=list(range(0, 61)), k=self.N_planes))
            self.ts_alive[0] = 100

        # reset dest
        self.dest.reset()

        # init state
        self._set_state()
        self.state_init = self.state
        return self.state

    def _spawn_plane(self, n:int=None, random:bool=False):
        """Spawns the n-th plane. Currently, the argument is not in use but might be relevant for some validation scenarios."""
        # sample heading and speed
        hdg = float(np.random.uniform(0.0, 360.0, size=1))
        tas = float(np.random.uniform(self.actas-3.0, self.actas+3.0, size=1))

        if random:
            qdr  = float(np.random.uniform(0.0, 360.0, size=1))
            dist = float(np.random.uniform(low=self.dest.radius, high=self.dest.spawn_radius, size=1))
        else:
            qdr  = hdg
            dist = self.dest.spawn_radius

        # determine origin
        lat, lon = qdrpos(latd1=self.dest.lat, lond1=self.dest.lon, qdr=qdr, dist=meter_to_NM(dist))

        # consider behavior type
        p = Plane(role="RL", dt=self.dt, actype=self.actype, lat=lat, lon=lon, alt=self.acalt, hdg=(hdg+180)%360, tas=tas)   

        # compute initial distance to destination
        p.D_dest     = latlondist(latd1=self.dest.lat, lond1=self.dest.lon, latd2=lat, lond2=lon)
        p.D_dest_old = copy(p.D_dest)
        return p

    def _set_state(self):
        # usual state of shape [N_planes, obs_size]
        if self.multi_policy:
            self.state = self._get_state_multi()

        # since we use a spatial-temporal recursive approach, we need multi-agent history as well
        else:
            self.state = self._get_state(0)

            if self.step_cnt == 0:
                self.s_multi_hist = np.zeros((self.history_length, self.N_planes, self.obs_size))                   
                self.hist_len = 0
                self.s_multi_old = np.zeros((self.N_planes, self.obs_size))
            else:
                # update history, where most recent state component is the old state from last step
                if self.hist_len == self.history_length:
                    self.s_multi_hist = np.roll(self.s_multi_hist, shift=-1, axis=0)
                    self.s_multi_hist[self.history_length - 1] = self.s_multi_old
                else:
                    self.s_multi_hist[self.hist_len] = self.s_multi_old
                    self.hist_len += 1

            # overwrite old state
            self.s_multi_old = self._get_state_multi()

    def _get_state_multi(self) -> None:
        """Computes the state in the multi-agent scenario."""
        s = np.zeros((self.N_planes, self.obs_size), dtype=np.float32)
        for i, _ in enumerate(self.planes):
            s[i] = self._get_state(i)
        return s

    def _get_state(self, i:int) -> np.ndarray:
        """Computes the state from the perspective of the i-th agent of the internal plane array.
        
        This is a np.array of size [3 + 4*(N_planes-1),] containing own relative bearing of goal, distance to goal, 
        common four information about target ships (relative speed, relative bearing, distance, heading intersection angle),
        and time until destination opens again."""

        # select plane of interest
        p = self.planes[i]

        # distance, bearing to goal, time alive, time to opening, time since open
        abs_bng_goal, d_goal = qdrdist(latd1=p.lat, lond1=p.lon, latd2=self.dest.lat, lond2=self.dest.lon) # outputs ABSOLUTE bearing
        bng_goal = angle_to_pi(angle_to_2pi(dtr(abs_bng_goal)) - dtr(p.hdg))
        s_i = np.array([bng_goal/np.pi,
                        NM_to_meter(d_goal)/self.dest.spawn_radius,
                        1.0-self.dest.t_nxt_open/self.dest.t_close,
                        1.0-self.dest.t_open_since/self.dest.t_close])
        if self.prio:
            s_i = np.append(s_i, [1.0 if self.ts_alive[i] == np.max(self.ts_alive) else -1.0])

        # information about other planes
        if self.N_planes > 1:
            TS_info = []
            for j, other in enumerate(self.planes):
                if i != j:
                    # relative speed
                    v_r = other.tas - p.tas

                    # bearing and distance
                    abs_bng, d = qdrdist(latd1=p.lat, lond1=p.lon, latd2=other.lat, lond2=other.lon)
                    bng = angle_to_pi(angle_to_2pi(dtr(abs_bng)) - dtr(p.hdg))/np.pi
                    d = NM_to_meter(d)/self.dest.spawn_radius

                    # heading intersection
                    C_T = angle_to_pi(np.radians(other.hdg - p.hdg))/np.pi

                    # aggregate
                    j_info = [d, bng, v_r, C_T]

                    # time alive
                    if self.prio:
                        j_info += [1.0 if self.ts_alive[j] == np.max(self.ts_alive) else -1.0]

                    TS_info.append(j_info)

            # sort array according to distance
            TS_info = np.hstack(sorted(TS_info, key=lambda x: x[0], reverse=True)).astype(np.float32)

            # ghost ship padding not needed since we always demand at least two planes
            # however, we need to pad NA's as usual in single-agent LSTMRecTD3
            if (not self.multi_policy):
                desired_length = self.obs_per_TS * (self.N_agents_max-1)
                TS_info = np.pad(TS_info, (0, desired_length - len(TS_info)), 'constant', constant_values=np.nan).astype(np.float32)

            s_i = np.concatenate((s_i, TS_info))
        return s_i

    def step(self, a):
        """Arg a:
        In multi-policy scenarios with continuous actions and no communication:
            np.array([N_planes, action_dim])

        In single-policy:
            _agent"""
        # increase step cnt and overall simulation time
        self.step_cnt += 1
        self.sim_t += self.dt
 
        # fly all planes in multi-policy situation
        if self.multi_policy:
            [p.upd_dynamics(a=a[i], discrete_acts=False, perf=self.perf, dest=None) for i, p in enumerate(self.planes)]

        # in single-policy situation, action corresponds to first plane, while the others are either RL or VFG
        else:
            cnt_agent:_Agent = a

            # collect states from planes
            states_multi = self._get_state_multi()

            for i, p in enumerate(self.planes):

                # fly planes depending on whether they are RL-, VFG-, or RND-controlled
                if p.role == "RL":

                    # spatial-temporal recurrent
                    act = cnt_agent.select_action(s        = states_multi[i], 
                                                  s_hist   = self.s_multi_hist[:, i, :], 
                                                  a_hist   = None, 
                                                  hist_len = self.hist_len)

                    # move plane
                    p.upd_dynamics(a=act, discrete_acts=False, perf=self.perf, dest=None)
                else:
                    raise NotImplementedError()

        # update live times
        if self.prio:
            self.ts_before_respawn = copy(self.ts_alive)
            self.ts_alive += 1

        # update distances to destination
        for p in self.planes:
            p.D_dest_old = copy(p.D_dest)
            p.D_dest = latlondist(latd1=p.lat, lond1=p.lon, latd2=self.dest.lat, lond2=self.dest.lon)

        # check destination entries
        entered_close, entered_open = self.dest.step(self.planes)

        # count accidents, incidents, false entries
        self._count_mistakes(entered_close)

        # respawning
        self._handle_respawn(entered_open)

        # compute state, reward, done        
        self._set_state()
        self._calculate_reward(entered_close, entered_open)
        d = self._done()

        if self.multi_policy:
            return self.state, self.r, d, {}
        else:
            return self.state, float(self.r[0]), d, {}

    def _handle_respawn(self, respawn_flags):
        """Respawns planes when they entered the open destination area or are at the outer simulation radius."""
        for i, p in enumerate(self.planes):
            if (p.D_dest >= self.dest.respawn_radius) or respawn_flags[i]:
                
                # spawn a plane
                self.planes[i] = self._spawn_plane(i, random=False)
                
                # reset living time only due to vertiport respawning
                if self.prio:
                    if respawn_flags[i]:
                        self.ts_alive[i] = 0

    def _calculate_reward(self, entered_close:np.ndarray, entered_open:np.ndarray):
        """Args:
            entered_close: np.ndarray([number_of_planes,]): who entered a closed destination
            entered_open:  np.ndarray([number_of_planes,]): who entered an open destination"""
        r_coll = np.zeros((self.N_planes, 1), dtype=np.float32)
        r_goal = np.zeros((self.N_planes, 1), dtype=np.float32)

        # ------- individual reward: collision & leaving map & goal-entering/-approaching -------
        D_matrix = np.ones((len(self.planes), len(self.planes))) * np.inf
        for i, pi in enumerate(self.planes):
            for j, pj in enumerate(self.planes):
                if i != j:
                    D_matrix[i][j] = latlondist(latd1=pi.lat, lond1=pi.lon, latd2=pj.lat, lond2=pj.lon)

        for i, pi in enumerate(self.planes):

            # collision
            D = float(np.min(D_matrix[i]))

            if D <= self.accident_dist:
                r_coll[i] -= 10.0

            elif D <= self.incident_dist:
                r_coll[i] -= 5.0

            else:
                r_coll[i] -= 1*np.exp(-D/(2*self.incident_dist))

            # off-map (+5 agains numerical issues)
            if pi.D_dest > (self.dest.spawn_radius + 5.0): 
                r_coll[i] -= 5.0

            # closed goal entering
            if entered_close[i]:
                r_goal[i] -= 5.0

            # open goal entering
            if entered_open[i]:

                # check whether only one vehicle entered
                if sum(entered_open) == 1:

                    if self.prio:
                        # check whether the vehicle had the longest living time
                        if self.ts_before_respawn[i] == np.max(self.ts_before_respawn):
                            r_goal[i] += 5.0

                        # otherwise punish
                        else:
                            r_goal[i] -= 5.0
                    else:
                        r_goal[i] += 5.0

                # bad if someone entered simultaneously
                else:
                    r_goal[i] -= 5.0

            # open goal approaching for the one who should go next
            if self.prio:
                if self.dest.was_open and (self.ts_before_respawn[i] == np.max(self.ts_before_respawn)):
                    r_goal[i] += (pi.D_dest_old - pi.D_dest)/5.0

        # ------------- collective reward: goal status ----------------
        # incentive structure
        if self.dest.is_open:
            r_goal -= 0.5 * self.dest.t_open_since/self.dest.t_close
        else:
            r_goal += 0.25

        # aggregate reward components
        r = (self.w_coll*r_coll + self.w_goal*r_goal)/self.w

        # store
        self.r = r
        self.r_coll = r_coll
        self.r_goal = r_goal

    def _done(self):
        # artificial done signal
        if self.step_cnt >= self._max_episode_steps:
            return True
        return False

    def _count_mistakes(self, entered_close):
        self.N_enterances_closed_d += sum(entered_close)
        for i, pi in enumerate(self.planes):
            for j, pj in enumerate(self.planes):
                if i < j:
                    D = latlondist(latd1=pi.lat, lond1=pi.lon, latd2=pj.lat, lond2=pj.lon)
                    if D <= self.accident_dist:
                        self.N_accs += 1
                    elif D <= self.incident_dist:
                        self.N_incs += 1
    def __str__(self):
        return f"Step: {self.step_cnt}, Sim-Time [s]: {int(self.sim_t)}, # Flight Taxis: {self.N_planes}" + "\n" +\
            f"Time-to-open [s]: {int(self.dest.t_nxt_open)}, Time-since-open[s]: {int(self.dest.t_open_since)}" + "\n" +\
                f"# Episode-Incidents: {self.N_incs}, # Episode-Accidents: {self.N_accs}" + "\n" +\
                f"# Episode-Closed Vertiport Enterances: {self.N_enterances_closed_d}"

    def render(self, mode=None):
        """Renders the current environment."""

        # plot every nth timestep
        if self.step_cnt % 1 == 0: 
            
            # init figure
            if len(plt.get_fignums()) == 0:
                if self.plot_reward and self.plot_state:
                    self.f = plt.figure(figsize=(14, 8))
                    self.gs  = self.f.add_gridspec(2, 2)
                    self.ax1 = self.f.add_subplot(self.gs[:, 0]) # ship
                    self.ax2 = self.f.add_subplot(self.gs[0, 1]) # reward
                    self.ax3 = self.f.add_subplot(self.gs[1, 1]) # state

                elif self.plot_reward:
                    self.f = plt.figure(figsize=(14, 8))
                    self.gs  = self.f.add_gridspec(1, 2)
                    self.ax1 = self.f.add_subplot(self.gs[0, 0]) # ship
                    self.ax2 = self.f.add_subplot(self.gs[0, 1]) # reward

                elif self.plot_state:
                    self.f = plt.figure(figsize=(14, 8))
                    self.gs  = self.f.add_gridspec(1, 2)
                    self.ax1 = self.f.add_subplot(self.gs[0, 0]) # ship
                    self.ax3 = self.f.add_subplot(self.gs[0, 1]) # state

                else:
                    self.f, self.ax1 = plt.subplots(1, 1, figsize=(10, 10))
                plt.ion()
                plt.show()           

            # storage
            if self.plot_reward:
                if self.step_cnt == 0:
                    if self.multi_policy:
                        self.ax2.r      = np.zeros((self.N_planes, self._max_episode_steps))
                        self.ax2.r_coll = np.zeros((self.N_planes, self._max_episode_steps))
                        self.ax2.r_goal = np.zeros((self.N_planes, self._max_episode_steps))
                    else:
                        self.ax2.r      = np.zeros(self._max_episode_steps)
                        self.ax2.r_coll = np.zeros(self._max_episode_steps)
                        self.ax2.r_goal = np.zeros(self._max_episode_steps)
                else:
                    if self.multi_policy:
                        self.ax2.r[:, self.step_cnt] = self.r.flatten()
                        self.ax2.r_coll[:, self.step_cnt] = self.r_coll.flatten()
                        self.ax2.r_goal[:, self.step_cnt] = self.r_goal.flatten()
                    else:
                        self.ax2.r[self.step_cnt] = self.r if isinstance(self.r, float) else float(self.r[0])
                        self.ax2.r_coll[self.step_cnt] = self.r_coll if isinstance(self.r_coll, float) else float(self.r_coll[0])
                        self.ax2.r_goal[self.step_cnt] = self.r_goal if isinstance(self.r_goal, float) else float(self.r_goal[0])

            if self.plot_state:
                if self.step_cnt == 0:
                    self.ax3.s = np.zeros((self.obs_size, self._max_episode_steps))
                else:
                    if self.multi_policy:
                        self.ax3.s[:, self.step_cnt] = self.state[0]
                    else:
                        self.ax3.s[:, self.step_cnt] = self.state

            # periodically clear and init
            if self.step_cnt % 50 == 0:

                # clearance
                self.ax1.clear()
                if self.plot_reward:
                    self.ax2.clear()
                if self.plot_state:
                    self.ax3.clear()

                # appearance
                self.ax1.set_title("Urban Air Mobility")
                self.ax1.set_xlabel("Lon [°]")
                self.ax1.set_ylabel("Lat [°]")
                self.ax1.set_xlim(9.985, 10.015)
                self.ax1.set_ylim(9.985, 10.015)

                if self.plot_reward:
                    self.ax2.set_xlabel("Timestep in episode")
                    self.ax2.set_ylabel("Reward of ID0")
                    self.ax2.set_xlim(0, 50*(np.ceil(self.step_cnt/50)+1))
                    self.ax2.set_ylim(-7, 7)

                if self.plot_state:
                    self.ax3.set_xlabel("Timestep in episode")
                    self.ax3.set_ylabel("State of Agent 0")
                    self.ax3.set_xlim(0, 50*(np.ceil(self.step_cnt/50)+1))
                    self.ax3.set_ylim(-2, 5)

                # ---------------- non-animated artists ----------------
                # spawning area
                lats, lons = map(list, zip(*[qdrpos(latd1=self.dest.lat, lond1=self.dest.lon, qdr=deg, dist=meter_to_NM(self.dest.spawn_radius))\
                    for deg in self.clock_degs]))
                self.ax1.plot(lons, lats, color="grey")

                # respawn area
                lats, lons = map(list, zip(*[qdrpos(latd1=self.dest.lat, lond1=self.dest.lon, qdr=deg, dist=meter_to_NM(self.dest.respawn_radius))\
                    for deg in self.clock_degs]))
                self.ax1.plot(lons, lats, color="black")

                # ---------- animated artists: initial drawing ---------
                # step info
                self.ax1.info_txt = self.ax1.text(x=9.9865, y=10.012, s="", fontdict={"size" : 9}, animated=True)

                # destination
                lats, lons = map(list, zip(*[qdrpos(latd1=self.dest.lat, lond1=self.dest.lon, qdr=deg, dist=meter_to_NM(self.dest.radius))\
                    for deg in self.clock_degs]))
                self.ax1.dest_ln = self.ax1.plot(lons, lats, color=self.dest.color, animated=True)[0]

                # aircraft information
                self.ax1.scs  = []
                self.ax1.lns  = []
                self.ax1.txts = []

                for i, p in enumerate(self.planes):

                    # show aircraft
                    self.ax1.scs.append(self.ax1.scatter([], [], marker=(3, 0, -p.hdg), color=COLORS[i], animated=True))

                    # incident area
                    self.ax1.lns.append(self.ax1.plot([], [], color=COLORS[i], animated=True)[0])

                    # information
                    self.ax1.txts.append(self.ax1.text(x=0.0, y=0.0, s="", color=COLORS[i], fontdict={"size" : 8}, animated=True))

                if self.plot_reward:
                    self.ax2.lns_agg  = []
                    self.ax2.lns_coll = []
                    self.ax2.lns_goal = []

                    if self.multi_policy:
                        for i in range(self.N_planes):
                            self.ax2.lns_agg.append(self.ax2.plot([], [], color=COLORS[i], label=f"Agg {i}", animated=True)[0])
                            self.ax2.lns_coll.append(self.ax2.plot([], [], color=COLORS[i], label=f"Collision {i}", linestyle="dotted", animated=True)[0])
                            self.ax2.lns_goal.append(self.ax2.plot([], [], color=COLORS[i], label=f"Goal {i}", linestyle="dashed", animated=True)[0])
                    else:
                        self.ax2.lns_agg.append(self.ax2.plot([], [], color=COLORS[0], label=f"Agg", animated=True)[0])
                        self.ax2.lns_coll.append(self.ax2.plot([], [], color=COLORS[1], label=f"Collision", animated=True)[0])
                        self.ax2.lns_goal.append(self.ax2.plot([], [], color=COLORS[2], label=f"Goal", animated=True)[0])

                    self.ax2.legend()

                if self.plot_state:
                    self.ax3.lns = []
                    for i in range(self.obs_size):
                        self.ax3.lns.append(self.ax3.plot([], [], label=self.obs_names[i], color=COLORS[i], animated=True)[0])
                    self.ax3.legend()

                # ----------------- store background -------------------
                self.f.canvas.draw()
                self.ax1.bg = self.f.canvas.copy_from_bbox(self.ax1.bbox)
                if self.plot_reward:
                    self.ax2.bg = self.f.canvas.copy_from_bbox(self.ax2.bbox)
                if self.plot_state:
                    self.ax3.bg = self.f.canvas.copy_from_bbox(self.ax3.bbox)
            else:

                # ------------- restore the background ---------------
                self.f.canvas.restore_region(self.ax1.bg)
                if self.plot_reward:
                    self.f.canvas.restore_region(self.ax2.bg)
                if self.plot_state:
                    self.f.canvas.restore_region(self.ax3.bg)

                # ----------- animated artists: update ---------------
                # step info
                self.ax1.info_txt.set_text(self.__str__())
                self.ax1.draw_artist(self.ax1.info_txt)

                # destination
                self.ax1.dest_ln.set_color(self.dest.color)
                self.ax1.draw_artist(self.ax1.dest_ln)

                for i, p in enumerate(self.planes):

                    # show aircraft
                    self.ax1.scs[i].set_offsets(np.array([p.lon, p.lat]))
                    self.ax1.draw_artist(self.ax1.scs[i])

                    # incident area
                    lats, lons = map(list, zip(*[qdrpos(latd1=p.lat, lond1=p.lon, qdr=deg, dist=meter_to_NM(self.incident_dist/2))\
                        for deg in self.clock_degs]))
                    self.ax1.lns[i].set_data(lons, lats) 
                    self.ax1.draw_artist(self.ax1.lns[i])

                    # information
                    s = f"id: {i}" + "\n" + f"hdg: {p.hdg:.1f}" + "\n" + f"alt: {p.alt:.1f}" + "\n" + \
                        f"tas: {p.tas:.1f}"

                    if hasattr(self, "ts_alive"):
                        s += "\n" + f"t alive: {int(self.ts_alive[i])}"
                        if self.ts_alive[i] == np.max(self.ts_alive):
                            s += " (Next!)"

                    if hasattr(p, "role"):
                        s += "\n" + f"role: {p.role}"
                    self.ax1.txts[i].set_text(s)
                    self.ax1.txts[i].set_position((p.lon, p.lat))
                    self.ax1.draw_artist(self.ax1.txts[i])

                # reward
                if self.plot_reward:
                    if self.multi_policy:
                        for i in range(self.N_planes):
                            self.ax2.lns_agg[i].set_data(np.arange(self.step_cnt+1), self.ax2.r[i][:self.step_cnt+1])
                            self.ax2.lns_coll[i].set_data(np.arange(self.step_cnt+1), self.ax2.r_coll[i][:self.step_cnt+1])
                            self.ax2.lns_goal[i].set_data(np.arange(self.step_cnt+1), self.ax2.r_goal[i][:self.step_cnt+1])

                            self.ax2.draw_artist(self.ax2.lns_agg[i])
                            self.ax2.draw_artist(self.ax2.lns_coll[i])
                            self.ax2.draw_artist(self.ax2.lns_goal[i])
                    else:
                        self.ax2.lns_agg[0].set_data(np.arange(self.step_cnt+1), self.ax2.r[:self.step_cnt+1])
                        self.ax2.lns_coll[0].set_data(np.arange(self.step_cnt+1), self.ax2.r_coll[:self.step_cnt+1])
                        self.ax2.lns_goal[0].set_data(np.arange(self.step_cnt+1), self.ax2.r_goal[:self.step_cnt+1])
                        
                        self.ax2.draw_artist(self.ax2.lns_agg[0])
                        self.ax2.draw_artist(self.ax2.lns_coll[0])
                        self.ax2.draw_artist(self.ax2.lns_goal[0])

                # state
                if self.plot_state:
                    for i in range(self.obs_size):
                        self.ax3.lns[i].set_data(np.arange(self.step_cnt+1), self.ax3.s[i][:self.step_cnt+1])
                        self.ax3.draw_artist(self.ax3.lns[i])

                # show it on screen
                self.f.canvas.blit(self.ax1.bbox)
                if self.plot_reward:
                    self.f.canvas.blit(self.ax2.bbox)
                if self.plot_state:
                    self.f.canvas.blit(self.ax3.bbox)
               
            plt.pause(0.05)
