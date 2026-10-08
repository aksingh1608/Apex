from apex_race import state_machine as sm


def test_has_eight_states():
    assert len(sm.STATES) == 8


def test_every_state_is_reachable_from_idle():
    seen = {sm.IDLE}
    frontier = [sm.IDLE]
    while frontier:
        s = frontier.pop()
        for (a, _), b in sm.TRANSITIONS.items():
            if a == s and b not in seen:
                seen.add(b)
                frontier.append(b)
    assert seen == set(sm.STATES)


def test_table_uses_known_states_and_events():
    for (a, e), b in sm.TRANSITIONS.items():
        assert a in sm.STATES and b in sm.STATES
        assert e in sm.EVENTS


def test_mission_path():
    s = sm.IDLE
    for e in [sm.START, sm.COUNTDOWN_DONE, sm.OBSTACLE, sm.BLOCKED, sm.PASSED,
              sm.PAUSE, sm.RESUME, sm.LAPS_DONE]:
        s = sm.next_state(s, e)
        assert s is not None
    assert s == sm.FINISHED


def test_unknown_event_is_ignored():
    assert sm.next_state(sm.IDLE, sm.OBSTACLE) is None
    assert sm.next_state(sm.FINISHED, sm.START) is None


def test_sentence_matches_example():
    text = sm.sentence(sm.RACING, sm.AVOID, sm.OBSTACLE, front=0.4249)
    assert text == "Obstacle 0.42 m ahead. RACING to AVOID."


def test_sentence_without_values():
    assert sm.sentence(sm.RACING, sm.AVOID, sm.OBSTACLE) == "Obstacle. RACING to AVOID."


def test_p_key_toggles():
    assert sm.key_to_event("p", sm.RACING) == sm.PAUSE
    assert sm.key_to_event("p", sm.PAUSED) == sm.RESUME
    assert sm.key_to_event("q", sm.RACING) is None
