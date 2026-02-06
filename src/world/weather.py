"""
ClawBots Weather System

Dynamic weather conditions per region.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import random
import math


class WeatherType(Enum):
    """Types of weather conditions."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    WINDY = "windy"
    SANDSTORM = "sandstorm"


class TimeOfDay(Enum):
    """Time periods."""
    DAWN = "dawn"       # 5:00 - 7:00
    MORNING = "morning" # 7:00 - 12:00
    NOON = "noon"       # 12:00 - 14:00
    AFTERNOON = "afternoon"  # 14:00 - 17:00
    EVENING = "evening"      # 17:00 - 20:00
    DUSK = "dusk"       # 20:00 - 21:00
    NIGHT = "night"     # 21:00 - 5:00


@dataclass
class WeatherState:
    """Current weather state for a region."""
    weather_type: WeatherType
    temperature: float  # Celsius
    humidity: float     # 0-100
    wind_speed: float   # km/h
    wind_direction: str # N, NE, E, SE, S, SW, W, NW
    visibility: float   # meters (0-10000)
    precipitation: float  # mm/h
    cloud_cover: float  # 0-100
    
    # Forecast
    changing_to: Optional[WeatherType] = None
    change_in_minutes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.weather_type.value,
            "temperature": round(self.temperature, 1),
            "humidity": round(self.humidity, 1),
            "wind_speed": round(self.wind_speed, 1),
            "wind_direction": self.wind_direction,
            "visibility": round(self.visibility),
            "precipitation": round(self.precipitation, 1),
            "cloud_cover": round(self.cloud_cover, 1),
            "forecast": {
                "changing_to": self.changing_to.value if self.changing_to else None,
                "change_in_minutes": self.change_in_minutes
            } if self.changing_to else None
        }


@dataclass
class RegionClimate:
    """Climate configuration for a region."""
    region: str
    
    # Temperature range (Celsius)
    temp_min: float = 10.0
    temp_max: float = 30.0
    
    # Common weather patterns (weights)
    weather_weights: Dict[WeatherType, float] = field(default_factory=dict)
    
    # Special conditions
    can_snow: bool = False
    can_sandstorm: bool = False
    always_clear: bool = False
    
    def __post_init__(self):
        if not self.weather_weights:
            self.weather_weights = {
                WeatherType.CLEAR: 30,
                WeatherType.CLOUDY: 25,
                WeatherType.OVERCAST: 15,
                WeatherType.LIGHT_RAIN: 10,
                WeatherType.RAIN: 8,
                WeatherType.HEAVY_RAIN: 4,
                WeatherType.STORM: 2,
                WeatherType.FOG: 4,
                WeatherType.WINDY: 2
            }


class WeatherEngine:
    """
    Manages weather simulation for all regions.
    """
    
    WIND_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    
    def __init__(self):
        self.climates: Dict[str, RegionClimate] = {}
        self.weather_states: Dict[str, WeatherState] = {}
        self.world_hour: float = 12.0  # Start at noon
        self.day_length_minutes: float = 60.0  # 60 real minutes = 24 game hours
        self._last_update = datetime.utcnow()
        self._init_default_climates()
        self._init_weather()
    
    def _init_default_climates(self):
        """Set up default region climates."""
        # Main hub - temperate
        self.climates["main"] = RegionClimate(
            region="main",
            temp_min=15.0,
            temp_max=28.0
        )
        
        # Market - slightly warmer, mostly clear
        self.climates["market"] = RegionClimate(
            region="market",
            temp_min=18.0,
            temp_max=32.0,
            weather_weights={
                WeatherType.CLEAR: 50,
                WeatherType.CLOUDY: 30,
                WeatherType.OVERCAST: 10,
                WeatherType.LIGHT_RAIN: 5,
                WeatherType.WINDY: 5
            }
        )
        
        # Forest - cooler, more rain
        self.climates["forest"] = RegionClimate(
            region="forest",
            temp_min=10.0,
            temp_max=25.0,
            weather_weights={
                WeatherType.CLEAR: 20,
                WeatherType.CLOUDY: 25,
                WeatherType.OVERCAST: 20,
                WeatherType.LIGHT_RAIN: 15,
                WeatherType.RAIN: 10,
                WeatherType.FOG: 8,
                WeatherType.WINDY: 2
            }
        )
        
        # Desert - hot, sandstorms
        self.climates["desert"] = RegionClimate(
            region="desert",
            temp_min=25.0,
            temp_max=45.0,
            can_sandstorm=True,
            weather_weights={
                WeatherType.CLEAR: 60,
                WeatherType.CLOUDY: 15,
                WeatherType.WINDY: 15,
                WeatherType.SANDSTORM: 10
            }
        )
        
        # Mountains - cold, snow possible
        self.climates["mountains"] = RegionClimate(
            region="mountains",
            temp_min=-5.0,
            temp_max=15.0,
            can_snow=True,
            weather_weights={
                WeatherType.CLEAR: 25,
                WeatherType.CLOUDY: 20,
                WeatherType.OVERCAST: 15,
                WeatherType.SNOW: 15,
                WeatherType.BLIZZARD: 5,
                WeatherType.FOG: 10,
                WeatherType.WINDY: 10
            }
        )
        
        # Beach - warm, tropical
        self.climates["beach"] = RegionClimate(
            region="beach",
            temp_min=22.0,
            temp_max=35.0,
            weather_weights={
                WeatherType.CLEAR: 40,
                WeatherType.CLOUDY: 25,
                WeatherType.LIGHT_RAIN: 15,
                WeatherType.RAIN: 10,
                WeatherType.STORM: 5,
                WeatherType.WINDY: 5
            }
        )
    
    def _init_weather(self):
        """Initialize weather for all regions."""
        for region in self.climates:
            self.weather_states[region] = self._generate_weather(region)
    
    def _generate_weather(self, region: str) -> WeatherState:
        """Generate weather state for a region."""
        climate = self.climates.get(region)
        if not climate:
            climate = RegionClimate(region=region)
        
        # Pick weather type based on weights
        weather_type = self._weighted_random(climate.weather_weights)
        
        # Calculate temperature based on time of day
        time_factor = math.sin((self.world_hour - 6) * math.pi / 12)  # Peak at noon
        temp_range = climate.temp_max - climate.temp_min
        base_temp = climate.temp_min + (temp_range * 0.5) + (temp_range * 0.3 * time_factor)
        
        # Adjust temp for weather
        temp_adjust = {
            WeatherType.CLEAR: 2,
            WeatherType.CLOUDY: 0,
            WeatherType.OVERCAST: -2,
            WeatherType.RAIN: -3,
            WeatherType.HEAVY_RAIN: -5,
            WeatherType.STORM: -4,
            WeatherType.SNOW: -8,
            WeatherType.BLIZZARD: -12,
            WeatherType.FOG: -1,
        }.get(weather_type, 0)
        
        temperature = base_temp + temp_adjust + random.uniform(-2, 2)
        
        # Other conditions based on weather type
        conditions = self._get_weather_conditions(weather_type)
        
        return WeatherState(
            weather_type=weather_type,
            temperature=temperature,
            humidity=conditions["humidity"],
            wind_speed=conditions["wind_speed"],
            wind_direction=random.choice(self.WIND_DIRECTIONS),
            visibility=conditions["visibility"],
            precipitation=conditions["precipitation"],
            cloud_cover=conditions["cloud_cover"]
        )
    
    def _get_weather_conditions(self, weather_type: WeatherType) -> Dict[str, float]:
        """Get conditions for a weather type."""
        conditions = {
            WeatherType.CLEAR: {
                "humidity": random.uniform(30, 50),
                "wind_speed": random.uniform(0, 10),
                "visibility": 10000,
                "precipitation": 0,
                "cloud_cover": random.uniform(0, 20)
            },
            WeatherType.CLOUDY: {
                "humidity": random.uniform(40, 60),
                "wind_speed": random.uniform(5, 15),
                "visibility": 8000,
                "precipitation": 0,
                "cloud_cover": random.uniform(40, 70)
            },
            WeatherType.OVERCAST: {
                "humidity": random.uniform(60, 80),
                "wind_speed": random.uniform(5, 20),
                "visibility": 5000,
                "precipitation": 0,
                "cloud_cover": random.uniform(80, 100)
            },
            WeatherType.LIGHT_RAIN: {
                "humidity": random.uniform(70, 85),
                "wind_speed": random.uniform(5, 15),
                "visibility": 4000,
                "precipitation": random.uniform(0.5, 2),
                "cloud_cover": random.uniform(70, 90)
            },
            WeatherType.RAIN: {
                "humidity": random.uniform(80, 95),
                "wind_speed": random.uniform(10, 25),
                "visibility": 2000,
                "precipitation": random.uniform(2, 7),
                "cloud_cover": random.uniform(85, 100)
            },
            WeatherType.HEAVY_RAIN: {
                "humidity": random.uniform(90, 100),
                "wind_speed": random.uniform(20, 40),
                "visibility": 500,
                "precipitation": random.uniform(7, 20),
                "cloud_cover": 100
            },
            WeatherType.STORM: {
                "humidity": random.uniform(85, 100),
                "wind_speed": random.uniform(40, 80),
                "visibility": 300,
                "precipitation": random.uniform(10, 30),
                "cloud_cover": 100
            },
            WeatherType.SNOW: {
                "humidity": random.uniform(70, 90),
                "wind_speed": random.uniform(5, 20),
                "visibility": 1500,
                "precipitation": random.uniform(1, 5),
                "cloud_cover": random.uniform(80, 100)
            },
            WeatherType.BLIZZARD: {
                "humidity": random.uniform(80, 100),
                "wind_speed": random.uniform(50, 100),
                "visibility": 50,
                "precipitation": random.uniform(5, 15),
                "cloud_cover": 100
            },
            WeatherType.FOG: {
                "humidity": random.uniform(90, 100),
                "wind_speed": random.uniform(0, 5),
                "visibility": random.uniform(50, 500),
                "precipitation": 0,
                "cloud_cover": random.uniform(30, 60)
            },
            WeatherType.WINDY: {
                "humidity": random.uniform(30, 50),
                "wind_speed": random.uniform(30, 60),
                "visibility": 7000,
                "precipitation": 0,
                "cloud_cover": random.uniform(20, 50)
            },
            WeatherType.SANDSTORM: {
                "humidity": random.uniform(10, 30),
                "wind_speed": random.uniform(50, 100),
                "visibility": random.uniform(10, 100),
                "precipitation": 0,
                "cloud_cover": random.uniform(50, 80)
            }
        }
        return conditions.get(weather_type, conditions[WeatherType.CLEAR])
    
    def _weighted_random(self, weights: Dict[WeatherType, float]) -> WeatherType:
        """Pick random weather type based on weights."""
        total = sum(weights.values())
        r = random.uniform(0, total)
        cumulative = 0
        for weather_type, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return weather_type
        return WeatherType.CLEAR
    
    def update(self, delta_seconds: float):
        """Update weather simulation."""
        # Update world time
        hours_per_second = 24.0 / (self.day_length_minutes * 60)
        self.world_hour += delta_seconds * hours_per_second
        if self.world_hour >= 24:
            self.world_hour -= 24
        
        # Random chance to change weather (5% per update)
        for region in self.weather_states:
            if random.random() < 0.05:
                # Schedule weather change
                current = self.weather_states[region]
                if not current.changing_to:
                    new_weather = self._generate_weather(region)
                    current.changing_to = new_weather.weather_type
                    current.change_in_minutes = random.randint(5, 30)
            
            # Process scheduled changes
            current = self.weather_states[region]
            if current.changing_to and current.change_in_minutes > 0:
                current.change_in_minutes -= 1
                if current.change_in_minutes <= 0:
                    self.weather_states[region] = self._generate_weather(region)
                    self.weather_states[region].weather_type = current.changing_to
    
    def get_weather(self, region: str) -> Optional[WeatherState]:
        """Get current weather for a region."""
        return self.weather_states.get(region)
    
    def get_all_weather(self) -> Dict[str, Dict]:
        """Get weather for all regions."""
        return {
            region: state.to_dict()
            for region, state in self.weather_states.items()
        }
    
    def get_time_of_day(self) -> TimeOfDay:
        """Get current time of day."""
        hour = self.world_hour
        if 5 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 14:
            return TimeOfDay.NOON
        elif 14 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 20:
            return TimeOfDay.EVENING
        elif 20 <= hour < 21:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT
    
    def get_world_time(self) -> Dict[str, Any]:
        """Get current world time info."""
        time_of_day = self.get_time_of_day()
        hour = int(self.world_hour)
        minute = int((self.world_hour - hour) * 60)
        
        return {
            "hour": hour,
            "minute": minute,
            "formatted": f"{hour:02d}:{minute:02d}",
            "time_of_day": time_of_day.value,
            "is_day": 6 <= hour < 20,
            "sun_position": math.sin((self.world_hour - 6) * math.pi / 12)
        }
    
    def force_weather(self, region: str, weather_type: WeatherType):
        """Force weather change (admin)."""
        if region in self.weather_states:
            self.weather_states[region] = self._generate_weather(region)
            self.weather_states[region].weather_type = weather_type


# Global instance
_weather_engine: Optional[WeatherEngine] = None


def get_weather_engine() -> WeatherEngine:
    """Get the global weather engine."""
    global _weather_engine
    if _weather_engine is None:
        _weather_engine = WeatherEngine()
    return _weather_engine
