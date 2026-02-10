DOMAIN = "action_timer"

##### model constants

# ActionTimerData keys
ID = "id"
DURATION = "duration"
CREATED_AT = "created_at"
EXPIRATION = "expiration"
ACTION_CONFIG = "action_config" 
RUN_ON_POWER_RESTORE = "run_on_power_restore"


##### service constants
SERVICE_SET_TIMER = "set_action_timer"
SERVICE_CANCEL_TIMER = "cancel_action_timer"


##### HA constants
SENSOR = "sensor"
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1