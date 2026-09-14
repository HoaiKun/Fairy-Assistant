def get_current_weather(location:str, unit:str = "celsius"):
    return {
        "location" : location,
        "temmperature" : 28,
        "unit" : unit,
        "condition": "rainy"
    }