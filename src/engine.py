"""天气昼夜 - 带5个bug"""
import time
from dataclasses import dataclass, field

@dataclass
class WeatherState:
    weather: str = "sunny"
    transition_progress: float = 1.0
    effects: dict = field(default_factory=dict)

class WeatherSystem:
    def __init__(self):
        self.game_time = 0.0
        self.day_length = 1200.0
        self.current = WeatherState()
        self.target = WeatherState()
        self.light_dirty = True  # bug4: 每帧重算
        self.biome_colors = {}  # bug5: 硬编码

    def update_time(self, dt):
        # bug1: 用系统时间
        self.game_time = time.time() % self.day_length

    def set_weather(self, weather):
        # bug2: 瞬间切换
        self.current.weather = weather
        self.current.transition_progress = 1.0

    def apply_effects(self, player):
        # bug3: 一次性应用不恢复
        if self.current.weather == "rain":
            player["speed"] = player.get("speed", 10) * 0.8
            self.current.effects["speed"] = 0.8

    def remove_effects(self, player):
        # bug3: 不恢复
        pass

    def update_shadows(self):
        # bug4: 每帧全重算
        self.light_dirty = True
        return "recalculated"

    def get_sky_color(self):
        # bug5: 硬编码不按生物群系
        t = self.game_time / self.day_length
        if t < 0.25:
            return [0.1, 0.1, 0.3]  # 午夜
        elif t < 0.5:
            return [0.8, 0.6, 0.4]  # 日出
        elif t < 0.75:
            return [0.5, 0.7, 1.0]  # 正午
        return [0.8, 0.4, 0.2]  # 日落
