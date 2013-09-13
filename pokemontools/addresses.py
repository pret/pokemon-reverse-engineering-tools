"""
Common methods used against addresses.
"""

def is_valid_address(address):
    """is_valid_rom_address"""
    if address == None:
        return False
    if type(address) == str:
        address = int(address, 16)
    if 0 <= address <= 2097152:
        return True
    else:
        return False
