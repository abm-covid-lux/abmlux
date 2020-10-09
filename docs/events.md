# Events

List of events

# Events Notifying of Simulation State Change
 * `sim.time.tick(clock, t)` --- Simulator time has updated to t, on the clock given
 * `sim.time.midnight(clock, t)` --- Simulator time is midnight
 * `sim.time.start_simulation(sim)` --- Simulator is about to start simulation (before first tick)
 * `sim.time.end_simulation(sim)` --- Simulator has finished simulation (after last tick)

 * `sim.agent.health(agent, old_health)` --- An agent's health status changed last tick
 * `sim.agent.activity(agent, old_activity)` --- An agent's activity status changed last tick
 * `sim.agent.location(agent, old_location)` --- An agent's location changed last tick

# Events Requesting Simulation Stage Change
 * `testing.book_test(agent)` --- the event in which an agent books a test
 * `testing.do_test(agent)` --- the event in which an agent is tested in the laboratory
 * `testing.result(agent, result)` --- the event in which an agent's test results are published

 * `quarantine.start(agent)` --- Agent should start quarantine
 * `quarantine.end(agent)` --- Agent should end quarantine

## Received by simulator
 * `agent.health.change(agent, health)` --- Agent should change health to the status given this tick
 * `agent.activity.change(agent, activity)` --- Agent should change activity to the status given this tick
 * `agent.location.change(agent, location)` --- Agent should change location to the status given this tick