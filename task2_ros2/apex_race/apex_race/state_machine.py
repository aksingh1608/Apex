"""Race state machine. One transition table, no ROS imports.

The controller turns sensor readings and key presses into events, then
asks this module for the next state. Anything not in the table is ignored.
"""

IDLE = "IDLE"
COUNTDOWN = "COUNTDOWN"
RACING = "RACING"
AVOID = "AVOID"
REPLAN = "REPLAN"
PAUSED = "PAUSED"
FINISHED = "FINISHED"
ABORTED = "ABORTED"

STATES = (IDLE, COUNTDOWN, RACING, AVOID, REPLAN, PAUSED, FINISHED, ABORTED)

# Events
START = "start"                  # key g
COUNTDOWN_DONE = "countdown_done"
OBSTACLE = "obstacle"            # something in the corridor ahead
PATH_CLEAR = "path_clear"        # the corridor ahead is empty again
BLOCKED = "blocked"              # still blocked after the hold time
PASSED = "passed"                # the racer is past the obstacle
PAUSE = "pause"                  # key p while moving
RESUME = "resume"                # key p while paused
ABORT = "abort"                  # key x
RESET = "reset"                  # key r
LAPS_DONE = "laps_done"

EVENTS = (START, COUNTDOWN_DONE, OBSTACLE, PATH_CLEAR, BLOCKED, PASSED,
          PAUSE, RESUME, ABORT, RESET, LAPS_DONE)

TRANSITIONS = {
    (IDLE, START): COUNTDOWN,
    (COUNTDOWN, COUNTDOWN_DONE): RACING,
    (COUNTDOWN, ABORT): ABORTED,
    (RACING, OBSTACLE): AVOID,
    (RACING, LAPS_DONE): FINISHED,
    (RACING, PAUSE): PAUSED,
    (RACING, ABORT): ABORTED,
    (AVOID, PATH_CLEAR): RACING,
    (AVOID, BLOCKED): REPLAN,
    (AVOID, PAUSE): PAUSED,
    (AVOID, ABORT): ABORTED,
    (REPLAN, PASSED): RACING,
    (REPLAN, OBSTACLE): AVOID,
    (REPLAN, LAPS_DONE): FINISHED,
    (REPLAN, PAUSE): PAUSED,
    (REPLAN, ABORT): ABORTED,
    (PAUSED, RESUME): RACING,
    (PAUSED, ABORT): ABORTED,
    (PAUSED, RESET): IDLE,
    (FINISHED, RESET): IDLE,
    (ABORTED, RESET): IDLE,
}

# States where the car may move under its own control.
MOVING = (RACING, AVOID, REPLAN)

REASONS = {
    START: "Start key pressed.",
    COUNTDOWN_DONE: "Countdown over.",
    OBSTACLE: "Obstacle {front:.2f} m ahead.",
    PATH_CLEAR: "Path ahead is clear again.",
    BLOCKED: "Obstacle still {front:.2f} m ahead after the hold time.",
    PASSED: "Racer is past the obstacle.",
    PAUSE: "Pause key pressed.",
    RESUME: "Resume key pressed.",
    ABORT: "Abort key pressed.",
    RESET: "Reset key pressed.",
    LAPS_DONE: "All laps done.",
}


def next_state(state, event):
    """Return the next state, or None if the event does nothing in this state."""
    return TRANSITIONS.get((state, event))


def sentence(old, new, event, **values):
    """Plain sentence for the log, for example
    "Obstacle 0.42 m ahead. RACING to AVOID."
    """
    reason = REASONS[event]
    try:
        reason = reason.format(**values)
    except (KeyError, ValueError):
        reason = (reason.split("{")[0].strip() or event) + "."
    return f"{reason} {old} to {new}."


def key_to_event(key, state):
    """Map a command key to an event. Key p pauses or resumes."""
    if key == "g":
        return START
    if key == "p":
        return RESUME if state == PAUSED else PAUSE
    if key == "x":
        return ABORT
    if key == "r":
        return RESET
    return None
