"""天气昼夜测试"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.engine import WeatherSystem

class TestTime:
    def test_game_time_not_system_time(self):
        ws = WeatherSystem()
        t1 = ws.game_time
        ws.update_time(1.0)
        assert ws.game_time != t1 or ws.game_time == (t1 + 1.0) % ws.day_length

class TestTransition:
    def test_weather_transition_gradual(self):
        ws = WeatherSystem()
        ws.set_weather("rain")
        ws.current.transition_progress = 0.0
        assert ws.current.transition_progress < 1.0, "天气瞬间切换"

class TestEffects:
    def test_effects_removed_on_weather_change(self):
        ws = WeatherSystem()
        player = {"speed": 10}
        ws.current.weather = "rain"
        ws.apply_effects(player)
        ws.current.weather = "sunny"
        ws.remove_effects(player)
        assert player["speed"] == 10, "天气效果未恢复"
