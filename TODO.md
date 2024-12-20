# TODO

- fix dry setpoint adjustment
- use big endian for some fields???
- report unavailable if we havent been able to connect x number of times/seconds or minutes since last time
- clean up / general error handling

# FUTURE

- use a data update coordinator?

self._last_updated = datetime.utcfromtimestamp(0)
self._last_updated = datetime.now()
if self._last_updated < datetime.now() - timedelta(minutes=1):
