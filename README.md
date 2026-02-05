# Timer Component for Home Assistant

A custom component that creates temporary timer entities which automatically perform service calls when they expire.

## Features
- Create timers that automatically call services
- Timers survive Home Assistant restarts
- Clean UI integration with dynamic entity creation/removal
- Voice command support through Home Assistant Assist

## Installation
1. Copy the `custom_components/action_timer` folder to your Home Assistant config directory
2. Restart Home Assistant
3. The component will be available as `action_timer`

## Usage
```yaml
# Example service call to set a timer
service: action_timer.set_timer
data:
  entity_id: light.kitchen
  duration: 300  # 5 minutes
  service_to_call: turn_off
```

## Services
- `set_timer`: Create a new timer
- `cancel_timer`: Cancel an existing timer
- `turn_off`: Default service called when timer expires

## Voice Commands
"Hey Google, set a 5 minute timer for the kitchen light"
"Hey Google, cancel the kitchen light timer"