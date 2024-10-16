from demo_00 import setup_sumo, get_options, start_sumo, run_simulation

def main():
    
    setup_sumo()    
    options = get_options()
    start_sumo(options)
    run_simulation()

if __name__ == "__main__":
    main()