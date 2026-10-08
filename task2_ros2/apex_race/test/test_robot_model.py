import pytest

from apex_race.robot_model import coloured_burger

SDF = ('<model name="turtlebot3_burger"><link name="base_link"></link>'
       "<publish_odom_tf>true</publish_odom_tf></model>")


def test_odom_tf_off_by_default():
    out = coloured_burger(SDF, "player", (0, 0, 1))
    assert "<publish_odom_tf>false</publish_odom_tf>" in out
    assert '<model name="player">' in out
    assert "apex_roof" in out


def test_odom_tf_kept_for_mapping():
    out = coloured_burger(SDF, "auto", (1, 0, 0), odom_tf=True)
    assert "<publish_odom_tf>true</publish_odom_tf>" in out


def test_missing_base_link():
    with pytest.raises(ValueError):
        coloured_burger("<model/>", "auto", (1, 0, 0))
