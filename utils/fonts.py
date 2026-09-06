"""
Font styling utility for Telegram messages and inline button labels.
Provides Unicode transformations (Monospace, Bold) since Telegram buttons
do not support markdown formatting.
"""

def to_mono(text: str) -> str:
    """Transform regular text to Unicode Monospace font (e.g. 𝙶𝚎𝚗𝚎𝚛𝚊𝚝𝚎 𝚂𝚎𝚜𝚜𝚒𝚘𝚗)."""
    res = []
    for c in text:
        if "A" <= c <= "Z":
            res.append(chr(ord(c) - ord("A") + 0x1D670))
        elif "a" <= c <= "z":
            res.append(chr(ord(c) - ord("a") + 0x1D68A))
        elif "0" <= c <= "9":
            res.append(chr(ord(c) - ord("0") + 0x1D7F6))
        else:
            res.append(c)
    return "".join(res)

def to_bold(text: str) -> str:
    """Transform regular text to Unicode Bold Sans font (e.g. 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗦𝗲𝘀𝘀𝗶𝗼𝗻)."""
    res = []
    for c in text:
        if "A" <= c <= "Z":
            res.append(chr(ord(c) - ord("A") + 0x1D5D4))
        elif "a" <= c <= "z":
            res.append(chr(ord(c) - ord("a") + 0x1D5EE))
        elif "0" <= c <= "9":
            res.append(chr(ord(c) - ord("0") + 0x1D7EC))
        else:
            res.append(c)
    return "".join(res)

def mb(text: str) -> str:
    """Format markdown text with bold monospace: **`text`**."""
    return f"**`{text}`**"
