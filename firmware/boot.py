"""ClaudeMicro boot config.

Enables the second USB CDC (data) channel used by the host bridge for
agent-status LED control, alongside the normal console channel.
"""
import usb_cdc
import usb_hid
import supervisor

supervisor.set_usb_identification(manufacturer="ClaudeMicro", product="ClaudeMicro Macropad")
usb_cdc.enable(console=True, data=True)
usb_hid.enable((usb_hid.Device.KEYBOARD, usb_hid.Device.CONSUMER_CONTROL))
