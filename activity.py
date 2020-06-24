


from enum import IntEnum

def create_activity_type(activity_map_config):
    """Returns an enum class, 'ActivityType', containing
    all of the labels in the activity mapping."""

    return IntEnum("ActivityType", list(activity_map_config.keys()), start=0, module="activity", qualname="activity.ActivityType")


