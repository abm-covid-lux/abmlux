"""Tests the clock"""

from datetime import timedelta,datetime

import pytest

import abmlux.sim_time as st


SECONDS_IN_A_MINUTE = 60
SECONDS_IN_AN_HOUR  = 60 * SECONDS_IN_A_MINUTE
SECONDS_IN_A_DAY    = 24 * SECONDS_IN_AN_HOUR
SECONDS_IN_A_WEEK   = 7 * SECONDS_IN_A_DAY


class TestSimClock:
    """Tests the simulation clock"""

    def test_initial_state(self):
        """Ensure the clock's initial state is as expected"""

        epoch = datetime(year=2020, month=1, day=1, hour=3, minute=5, second=20)
        clock = st.SimClock(1, simulation_length_days=5, epoch=epoch)

        clock.max_ticks = 5 * SECONDS_IN_A_DAY

        # How many ticks through the week are we?  2020/01/01 was a Wednesday, which is
        # 3 days through the week
        assert clock.epoch_week_offset == 2 * SECONDS_IN_A_DAY \
                                        + 3 * SECONDS_IN_AN_HOUR \
                                        + 5 * SECONDS_IN_A_MINUTE \
                                        + 20

        # Clock hasn't started yet
        assert not clock.started

        # Everything should be zero
        assert clock.seconds_elapsed() == 0
        assert clock.time_elapsed() == timedelta(0)
        assert clock.minutes_elapsed() == 0
        assert clock.hours_elapsed() == 0
        assert clock.days_elapsed() == 0
        assert clock.weeks_elapsed() == 0

        # We have started at the epoch
        assert clock.now() == epoch

        # Length of clock is always the max ticks
        assert len(clock) == 5 * SECONDS_IN_A_DAY
        assert len(clock) == clock.max_ticks

        assert clock.time_remaining() == timedelta(days=5)

    def test_duration(self):
        """Tests max clock duration"""

        clock = st.SimClock(1, simulation_length_days=1)

        assert clock.max_ticks == SECONDS_IN_A_DAY

        for t in clock:
            pass
        assert clock.t == SECONDS_IN_A_DAY


    def test_weekly_counter(self):
        """Tests weekly counter"""

        tick_length = 600

        epoch = datetime(year=2020, month=1, day=1, hour=3, minute=5, second=20)
        clock = st.SimClock(tick_length, simulation_length_days=35, epoch=epoch)


        # Ticks through the week is going to be ticks mod ticks_in_a_week
        assert clock.ticks_in_week == (SECONDS_IN_A_WEEK / tick_length)

        now = epoch
        for t in clock:
            assert clock.now() == now
            assert clock.now().weekday() == now.weekday()

            start_of_week = now - timedelta(seconds=now.weekday() * SECONDS_IN_A_DAY \
                                            + now.hour * SECONDS_IN_AN_HOUR \
                                            + now.minute * SECONDS_IN_A_MINUTE \
                                            + now.second)
            seconds_through_week = (now - start_of_week).total_seconds()
            ticks_through_week = int(seconds_through_week / tick_length)
            if seconds_through_week < tick_length:
                ticks_through_week = 0

            assert clock.ticks_through_week() == ticks_through_week

            now += timedelta(seconds=tick_length)

    def test_tick_length_check(self):
        """Tests tick length"""

        with pytest.raises(ValueError):
            st.SimClock(1723)

    def test_number_of_ticks_elapsed(self):
        """Tests elapsed tick calculation"""

        clock = st.SimClock(600, 100)

        count = 0
        for t in clock:
            count += 1

        assert count == (100 * SECONDS_IN_A_DAY) / 600

    def test_clock_reset(self):
        """Tests resetting of clock"""

        clock = st.SimClock(600, 100)

        # Run the clock
        t = next(clock)
        assert t == 0
        t = next(clock)
        assert t == 1
        assert clock.started

        clock.reset()
        assert not clock.started

        # re-run the clock
        t = next(clock)
        assert t == 0
        t = next(clock)
        assert t == 1
        assert clock.started
