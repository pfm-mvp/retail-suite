# Bron: jij gaf ID -> Naam
SHOP_NAME_MAP = {
    32224: "Amersfoort",
    31977: "Amsterdam",
    31831: "Den Bosch",
    32872: "Haarlem",
    32319: "Leiden",
    32871: "Maastricht",
    30058: "Nijmegen",
    32320: "Rotterdam",
    32204: "Venlo"
}

# Handige afgeleiden:
SHOP_ID_TO_NAME = SHOP_NAME_MAP
SHOP_NAME_TO_ID = {v: k for k, v in SHOP_NAME_MAP.items()}
