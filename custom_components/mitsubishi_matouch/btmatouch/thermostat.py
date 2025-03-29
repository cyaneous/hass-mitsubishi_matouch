"""Class representing a Mitsubishi MA Touch BLE thermostat."""

import logging
import asyncio
from types import TracebackType
from typing import Self

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from construct import StreamError

from ._structures import (
    _MAMessageHeader,
    _MAMessageFooter,
    _MARequest,
    _MAResponse,
    _MAAuthenticatedRequest,
    _MAStatusRequest,
    _MAStatusResponse,
    _MAControlRequest,
    _MAControlResponse,
)
from .const import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONNECTION_TIMEOUT,
    MAOperationMode,
    _MACharacteristic,
    _MAMessageType,
    _MAResult,
    _MAOperationModeFlags,
    MAVaneMode,
    MAFanMode,
)
from .exceptions import (
    MAAlreadyAwaitingResponseException,
    MARequestException,
    MAConnectionException,
    MAInternalException,
    MAResponseException,
    MAAuthException,
    MAStateException,
    MATimeoutException,
)
from .models import Status

__all__ = ["Thermostat"]

_LOGGER = logging.getLogger(__name__)


class Thermostat:
    """Representation of a Mitsubishi MA Touch thermostat."""

    def __init__(
        self,
        pin: int,
        ble_device: BLEDevice,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
    ):
        """Initialize the thermostat.

        The thermostat will be in a disconnected state after initialization.

        Args:
            mac_address (str): The MAC address of the thermostat.
            pin (int): The PIN for accessing the thermostat (hex representation).
            connection_timeout (int, optional): The connection timeout in seconds. Defaults to DEFAULT_CONNECTION_TIMEOUT.
            command_timeout (int, optional): The command timeout in seconds. Defaults to DEFAULT_COMMAND_TIMEOUT.
        """

        self._mac_address = ble_device.address
        self._pin = pin
        self._ble_device = ble_device
        self._connection_timeout = connection_timeout
        self._command_timeout = command_timeout

        self._firmware_version: str | None = None
        self._software_version: str | None = None

        # TODO: hass docs recommend not reusing BleakClient between connections to avoid connection instability?
        self._conn: BleakClient = BleakClient(
            self._ble_device,
            disconnected_callback=self._on_disconnected,
            timeout=DEFAULT_CONNECTION_TIMEOUT,
        )
        self._connection_lock = asyncio.Lock()
        self._gatt_lock = asyncio.Lock()
        self._response_future: asyncio.Future[bytes] | None = None

        self._message_id = 0
        self._receive_length = 0
        self._receive_buffer = bytes(0)

    @property
    def is_connected(self) -> bool:
        """Check if the thermostat is connected.

        Returns:
            bool: True if connected, False otherwise.
        """

        return self._conn.is_connected

    @property
    def firmware_version(self) -> str | None:
        """Get the thermostat firmware version."""

        return self._firmware_version

    @property
    def software_version(self) -> str | None:
        """Get the thermostat software version."""

        return self._software_version

    async def async_connect(self) -> None:
        """Connect to the thermostat.

        After connecting, the device data and status will be queried and stored.

        Raises:
            MAStateException: If the thermostat is already connected.
            MAConnectionException: If the connection fails.
            MATimeoutException: If the connection times out.
            MARequestException: If an error occurs while sending a command.
        """

        if self.is_connected:
            raise MAStateException("Already connected")

        _LOGGER.debug("[%s] Connecting...", self._mac_address)

        self._message_id = 0

        try:
            await self._conn.connect()

            _LOGGER.debug("[%s] Connected!", self._mac_address)

            await self._conn.start_notify(
                _MACharacteristic.NOTIFY, self._on_message_received
            )

            if self._firmware_version is None or self._software_version is None:
                self._firmware_version = await self._async_read_char_str(_MACharacteristic.FIRMWARE_VERSION)
                self._software_version = await self._async_read_char_str(_MACharacteristic.SOFTWARE_VERSION)
                _LOGGER.debug("[%s] Firmware version: %s, software version: %s", self._mac_address, self._firmware_version, self._software_version)
        except BleakError as ex:
            _LOGGER.debug("[%s] BleakError: %s", self._mac_address, ex)
            raise MAConnectionException("Could not connect to the device") from ex
        except TimeoutError as ex:
            _LOGGER.debug("[%s] TimeoutError: %s", self._mac_address, ex)
            raise MATimeoutException("Timeout during connection") from ex

    async def async_disconnect(self) -> None:
        """Disconnect from the thermostat.

        Before disconnection all pending futures will be cancelled.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAConnectionException: If the disconnection fails.
            MATimeoutException: If the disconnection times out.
        """

        if not self.is_connected:
            raise MAStateException("No need to disconnect - not connected")

        exception = MAConnectionException("Connection closed")

        if self._response_future is not None and not self._response_future.done():
            self._response_future.set_exception(exception)

        try:
            await self._conn.disconnect()
        except EOFError:
            pass
        except BleakError as ex:
            raise MAConnectionException("Could not disconnect from the device") from ex
        except TimeoutError as ex:
            raise MATimeoutException("Timeout during disconnection") from ex

    async def async_login(self, pin: int) -> None:
        """Authentication, etc via unknown messages.

        Raises:
            MAStateException: If the thermostat is not connected.
            MARequestException: If an error occurs while sending the command.
            MATimeoutException: If the command times out.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MAAuthException: If the PIN is incorrect.
        """

        request = _MAAuthenticatedRequest(message_type=_MAMessageType.LOGIN_REQUEST, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

        # not sure what this does yet, but seems to be required
        request = _MAAuthenticatedRequest(message_type=_MAMessageType.UNKNOWN_1, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

        # not sure what this does yet, but seems to be required
        request = _MAAuthenticatedRequest(message_type=_MAMessageType.UNKNOWN_2, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

    async def async_logout(self, pin: int) -> None:
        """Unknown messages at end of connection.

        Raises:
            MAStateException: If the thermostat is not connected.
            MARequestException: If an error occurs while sending the command.
            MATimeoutException: If the command times out.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MAAuthException: If the PIN is incorrect.
        """

        # not sure what this does yet, but seems to be required
        request = _MAAuthenticatedRequest(message_type=_MAMessageType.UNKNOWN_3, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

        # not sure what this does yet, but seems to be required
        request = _MAAuthenticatedRequest(message_type=_MAMessageType.UNKNOWN_4, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

        # not sure what this does yet, but seems to be required
        request = _MAAuthenticatedRequest(message_type=_MAMessageType.UNKNOWN_5, request_flag=0x01, pin=pin)
        await self._async_write_request(request)

    async def async_get_status(self) -> Status:
        """Query the latest status.

        Returns:
            Status: The status.

        Raises:
            MAStateException: If the thermostat is not connected.
            MARequestException: If an error occurs while sending the command.
            MATimeoutException: If the command times out.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MAResponseException: If the status update response was invalid.
        """

        request = _MAStatusRequest(message_type=_MAMessageType.STATUS_REQUEST, request_flag=0x00)
        response_bytes = await self._async_write_request(request)
        response = _MAStatusResponse.from_bytes(response_bytes)
        status = Status._from_struct(response)
        _LOGGER.debug("[%s] Status payload: %s", self._mac_address, response_bytes.hex())
        _LOGGER.debug("[%s] Status IN: %s", self._mac_address, vars(response))
        #_LOGGER.debug("[%s] Status OUT: %s", self._mac_address, vars(status))
        return status

    async def async_set_cool_setpoint(self, temperature: float) -> None:
        """Set the heating setpoint temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.

        Args:
            temperature (float): The new target temperature in degrees Celsius.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MARequestException: If an error occurs during the command.
            MATimeoutException: If the command times out.
            MAResponseException: If the temperature is invalid.
        """

        await self._async_write_control_request(
            flags_b=0x01,
            cool_setpoint=temperature
        )

    async def async_set_heat_setpoint(self, temperature: float) -> None:
        """Set the heating setpoint temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.

        Args:
            temperature (float): The new target temperature in degrees Celsius.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MARequestException: If an error occurs during the command.
            MATimeoutException: If the command times out.
            MAResponseException: If the temperature is invalid.
        """

        await self._async_write_control_request(
            flags_b=0x02,
            heat_setpoint=temperature
        )

    async def async_set_operation_mode(self, operation_mode: MAOperationMode) -> None:
        """Set the operation mode.

        Args:
            operation_mode (MAOperationMode): The new operation mode.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MARequestException: If an error occurs during the command.
            MATimeoutException: If the command times out.
            MAResponseException: If the operation mode is not supported.
        """

        match operation_mode:
            case MAOperationMode.OFF:
                await self._async_write_control_request(
                    flags_a=0x01,
                    operation_mode_flags=_MAOperationModeFlags.HEAT,
                )
            case _:
                await self._async_write_control_request(
                    flags_a=0x01,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.HEAT,
                )

        match operation_mode:
            case MAOperationMode.AUTO:
                await self._async_write_control_request(
                    flags_a=0x02,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.AUTO|_MAOperationModeFlags.HEAT|_MAOperationModeFlags.COOL|_MAOperationModeFlags.DRY,
                )
            case MAOperationMode.HEAT:
                await self._async_write_control_request(
                    flags_a=0x02,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.HEAT
                )
            case MAOperationMode.COOL:
                await self._async_write_control_request(
                    flags_a=0x02,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.COOL
                )
            case MAOperationMode.DRY:
                await self._async_write_control_request(
                    flags_a=0x02,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.HEAT|_MAOperationModeFlags.DRY
                )
            case MAOperationMode.FAN:
                await self._async_write_control_request(
                    flags_a=0x02,
                    operation_mode_flags=_MAOperationModeFlags.POWER|_MAOperationModeFlags.FAN
                )

    async def async_set_fan_mode(self, fan_mode: MAFanMode) -> None:
        """Set the fan mode.

        Args:
            fan_mode (MAFanMode): The new fan mode.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MARequestException: If an error occurs during the command.
            MATimeoutException: If the command times out.
            MAResponseException: If the fan_mode is invalid.
        """

        await self._async_write_control_request(
            flags_c=0x01,
            fan_mode=fan_mode
        )

    async def async_set_vane_mode(self, vane_mode: MAVaneMode) -> None:
        """Set the vane mode.

        Args:
            vane_mode (MAVaneMode): The new vane mode.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAAlreadyAwaitingResponseException: If a status command is already pending.
            MARequestException: If an error occurs during the command.
            MATimeoutException: If the command times out.
            MAResponseException: If the vane_mode is invalid.
        """

        await self._async_write_control_request(
            flags_c=0x02,
            vane_mode=vane_mode
        )

    ### Internal ###

    async def __aenter__(self) -> Self:
        """Async context manager enter.

        Connects to the thermostat. After connecting, authentication will be performed.

        Raises:
            MAStateException: If the thermostat is already connected.
            MAConnectionException: If the connection fails.
            MATimeoutException: If the connection times out.
            MARequestException: If an error occurs while sending a command.
        """

        await self._connection_lock.acquire()

        try:
            await self.async_connect()
            await self.async_login(pin=self._pin)
        except Exception as ex:
            if self.is_connected:
                try:
                    await self.async_disconnect()
                except Exception:
                    pass
            self._connection_lock.release()
            raise ex

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Async context manager exit.

        Disconnects from the thermostat. Before disconnection all pending futures will be cancelled.

        Raises:
            MAStateException: If the thermostat is not connected.
            MAConnectionException: If the disconnection fails.
            MATimeoutException: If the disconnection times out.
        """

        try:
            if self.is_connected:
                if exc_value is not None: # ignore exceptions if we already have one coming
                    try:
                        await self.async_disconnect()
                    except Exception:
                        pass
                else:
                    await self.async_logout(pin=self._pin)
                    await self.async_disconnect()
        finally:
            self._connection_lock.release()

    async def _async_read_char_str(self, uuid: str) -> str:
        return "".join(map(chr, await self._async_read_char(uuid)))

    async def _async_read_char(self, uuid: str) -> bytearray:
        """Read a device characteristic.

        Args:
            uuid (str): The uuid of the characteristic to read

        Raises:
            MAStateException: If the thermostat is not connected.
            MARequestException: If an error occurs while sending the command.
            MATimeoutException: If the command times out.
        """

        if not self.is_connected:
            raise MAStateException("Cannot read char - not connected")

        async with self._gatt_lock:
            try:
                return await self._conn.read_gatt_char(uuid)
            except BleakError as ex:
                raise MARequestException("Error during read") from ex
            except TimeoutError as ex:
                raise MATimeoutException("Timeout during read") from ex

    async def _async_write_request(self, request: _MARequest) -> bytes:
        """Write a request to the thermostat.

        Args:
            command (_MARequest): The command to write.

        Raises:
            MAStateException: If the thermostat is not connected.
            MARequestException: If an error occurs while sending the command.
            MATimeoutException: If the command times out.
        """

        _LOGGER.debug("[%s] _async_write_request() called", self._mac_address)

        if not self.is_connected:
            raise MAStateException("Cannot write request - not connected")

        if self._response_future is not None:
            raise MAAlreadyAwaitingResponseException(
                "Already awaiting a command response"
            )

        # TODO: clean this up
        payload = request.to_bytes()
        message = _MAMessageHeader(length=(1 + len(payload) + 2), message_id=self._message_id).to_bytes()
        message += payload
        message += _MAMessageFooter(crc=self._crc_sum(message)).to_bytes()

        self._message_id = self._message_id + 1 if self._message_id < 0x07 else 0

        self._response_future = asyncio.Future()

        async with self._gatt_lock:
            try:
                for i in range(0, len(message), 20):
                    part = message[i:i+20]
                    _LOGGER.debug("[%s] SND: %s", self._mac_address, part.hex())
                    await self._conn.write_gatt_char(_MACharacteristic.WRITE, part, response=False)
            except BleakError as ex:
                self._response_future = None
                raise MARequestException(f"Error during request write: {ex}") from ex
            except TimeoutError as ex:
                self._response_future = None
                raise MATimeoutException("Timeout during request write") from ex

        try:
            response_bytes = await asyncio.wait_for(self._response_future, self._command_timeout)
            response_header = _MAResponse.from_bytes(response_bytes)
            if response_header.message_type != request.message_type & 0xff:
                raise MAResponseException(f"Incorrect response message type received: {response_header.message_type}")
            match response_header.result:
                case _MAResult.SUCCESS:
                    return response_bytes
                case _MAResult.IN_MENUS:
                    raise MAResponseException(f"Failure result received: {response_header.result} - thermostat in menus?")
                case _MAResult.BAD_PIN:
                    raise MAAuthException("Failure result received: Incorrect PIN?")
                case _MAResult.UNKNOWN_3_BAD_PIN:
                    raise MAAuthException("Failure result received: Incorrect PIN?")
                case _:
                    raise MAResponseException(f"Failure result received: {response_header.result}")
        except TimeoutError as ex:
            raise MATimeoutException("Timeout while awaiting response") from ex
        except StreamError as ex:
            raise MAResponseException(f"Failed to parse response header: {ex}") from ex
        finally:
            self._response_future = None

    async def _async_write_control_request(
        self,
        flags_a: int = 0,
        flags_b: int = 0,
        flags_c: int = 0,
        operation_mode_flags: _MAOperationModeFlags = _MAOperationModeFlags.NONE,
        cool_setpoint: float = 0,
        heat_setpoint: float = 0,
        fan_mode: MAFanMode = MAFanMode.NONE,
        vane_mode: MAVaneMode = MAVaneMode.NONE
    ) -> None:
        request = _MAControlRequest(
            message_type=_MAMessageType.CONTROL_REQUEST,
            request_flag=0x01,
            flags_a=flags_a,
            flags_b=flags_b,
            flags_c=flags_c,
            operation_mode_flags=operation_mode_flags,
            cool_setpoint=cool_setpoint,
            heat_setpoint=heat_setpoint,
            unknown_setpoint_1=0,
            unknown_setpoint_2=0,
            unknown_setpoint_3=0,
            vane_fan_mode=(vane_mode.value << 4) + (fan_mode.value >> 4)
        )

        response_bytes = await self._async_write_request(request)
        response = _MAControlResponse.from_bytes(response_bytes)
        # TODO: error check for success?

    def _crc_sum(self, frame: bytes) -> int:
        """Calculate frame CRC."""

        return sum(frame) & 0xff

    def _on_disconnected(self, _: BleakClient) -> None:
        """Handle disconnection from the thermostat."""

        _LOGGER.debug("[%s] Disconnected.", self._mac_address)

    async def _on_message_received(self, _: BleakGATTCharacteristic, data: bytearray) -> None:
        """Handle received messages from the thermostat."""

        _LOGGER.debug("[%s] RCV: %s", self._mac_address, data.hex())

        data_bytes = bytes(data)

        if self._receive_length == 0:
            header = _MAMessageHeader.from_bytes(data_bytes)
            if header.length > 64:
                raise MAInternalException(f"Received message too long: {header.length}")

            self._receive_length = header.length
            self._receive_buffer = data_bytes[2:]
        else:
            self._receive_buffer += data_bytes

        if len(self._receive_buffer) != self._receive_length:
            return

        self._receive_length = 0
        payload = self._receive_buffer[1:-2]
        crc = self._receive_buffer[:2]

        # TODO: check checksum

        if self._response_future is not None:
            self._response_future.set_result(payload)
        else:
            raise MAInternalException(f"Unsolicited message received, payload: {payload}")
