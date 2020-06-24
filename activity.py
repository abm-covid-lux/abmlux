


from enum import IntEnum


class ActivityManager:

    def __init__(self, activity_map_config):
        self.map_config = activity_map_config
        self.map_class  = self.get_activity_type_class()

    def get_activity_type_class(self):
        """Returns an enum class, 'ActivityType', containing
        all of the labels in the activity mapping.

        To use, call this and assign to the class name ActivityType, e.g.
        ActivityType = create_activity_type(config['activity_mapping'])
        """
        return IntEnum("ActivityType", list(self.map_config.keys()), \
                       start=0, module="activity", qualname="activity.ActivityType")

    def get_location_types(self, activity_type):
        """For a given activity type (int or enum), return a list of
        location types that can be used by agents to perform this activity."""

        # If this is a string, convert to the ActivityType class
        if isinstance(activity_type, str):
            activity_type = self.map_class[activity_type]
        elif isinstance(activity_type, int):
            activity_type = self.map_class(activity_type)

        # Look up from config using the name
        if activity_type.name in self.map_config \
           and 'allowed_locations' in self.map_config[activity_type.name]:
            return self.map_config[activity_type.name]['allowed_locations']
        return []

