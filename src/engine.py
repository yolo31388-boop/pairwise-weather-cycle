"""天气昼夜系统"""
from dataclasses import dataclass, field

# 昼夜关键帧: 名称 -> (时刻 0~1, 默认颜色)
KEYFRAME_TIMES = {
    "midnight": 0.0,
    "sunrise": 0.25,
    "noon": 0.5,
    "sunset": 0.75,
}

# 按生物群系的关键帧颜色配置
DEFAULT_BIOME_COLORS = {
    "plains": {
        "midnight": [0.1, 0.1, 0.3],
        "sunrise": [0.8, 0.6, 0.4],
        "noon": [0.5, 0.7, 1.0],
        "sunset": [0.8, 0.4, 0.2],
    },
    "desert": {
        "midnight": [0.15, 0.1, 0.25],
        "sunrise": [0.95, 0.7, 0.35],
        "noon": [0.9, 0.85, 0.7],
        "sunset": [0.9, 0.45, 0.15],
    },
    "snow": {
        "midnight": [0.05, 0.08, 0.2],
        "sunrise": [0.7, 0.65, 0.75],
        "noon": [0.75, 0.85, 1.0],
        "sunset": [0.6, 0.4, 0.5],
    },
}

# 天气渲染参数: 光照颜色 / 粒子密度
WEATHER_PROFILES = {
    "sunny": {"light_color": [1.0, 0.98, 0.9], "particle_density": 0.0},
    "cloudy": {"light_color": [0.7, 0.72, 0.78], "particle_density": 0.1},
    "rain": {"light_color": [0.5, 0.55, 0.65], "particle_density": 0.7},
    "storm": {"light_color": [0.3, 0.32, 0.42], "particle_density": 1.0},
    "snow": {"light_color": [0.8, 0.85, 0.95], "particle_density": 0.6},
}

# 天气对属性的修饰器: 属性 -> ("mul"|"add", 值)
WEATHER_MODIFIERS = {
    "rain": {"speed": ("mul", 0.8)},
    "storm": {"speed": ("mul", 0.6)},
    "snow": {"speed": ("mul", 0.7)},
}


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return [_lerp(x, y, t) for x, y in zip(c1, c2)]


@dataclass
class WeatherState:
    weather: str = "sunny"
    transition_progress: float = 1.0
    effects: dict = field(default_factory=dict)


class WeatherSystem:
    def __init__(self):
        self.game_time = 0.0
        self.day_length = 1200.0
        self.paused = False
        self.time_scale = 1.0
        self.current = WeatherState()
        self.target = WeatherState()
        self.transition_duration = 5.0
        self.light_dirty = False
        self.light_threshold = 0.05
        self.shadow_chunks = 4  # 阴影分帧更新批数
        self._shadow_chunks_done = 0
        self._last_light_color = None
        self.biome = "plains"
        self.biome_colors = {k: {n: list(c) for n, c in v.items()}
                             for k, v in DEFAULT_BIOME_COLORS.items()}

    # ---- 时间: 游戏内累积时间, 支持暂停与缩放 ----
    def update_time(self, dt):
        if self.paused:
            return
        self.game_time = (self.game_time + dt * self.time_scale) % self.day_length

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_time_scale(self, scale):
        self.time_scale = scale

    # ---- 天气转换: 带过渡时长, 按进度插值 ----
    def set_weather(self, weather):
        if weather == self.target.weather and self.current.transition_progress < 1.0:
            return
        if weather == self.current.weather:
            return
        self.target.weather = weather
        self.current.transition_progress = 0.0

    def update_transition(self, dt):
        if self.current.transition_progress >= 1.0:
            return
        self.current.transition_progress = min(
            1.0, self.current.transition_progress + dt / self.transition_duration)
        if self.current.transition_progress >= 1.0:
            self.current.weather = self.target.weather

    def update(self, dt):
        self.update_time(dt)
        self.update_transition(dt)
        self.update_lighting()

    def _weather_profile(self, weather):
        return WEATHER_PROFILES.get(weather, WEATHER_PROFILES["sunny"])

    def get_light_color(self):
        t = self.current.transition_progress
        src = self._weather_profile(self.current.weather)["light_color"]
        dst = self._weather_profile(self.target.weather)["light_color"]
        return _lerp_color(src, dst, t)

    def get_particle_density(self):
        t = self.current.transition_progress
        src = self._weather_profile(self.current.weather)["particle_density"]
        dst = self._weather_profile(self.target.weather)["particle_density"]
        return _lerp(src, dst, t)

    # ---- 天气效果: 可恢复的修饰器模式 ----
    def apply_effects(self, player):
        modifiers = WEATHER_MODIFIERS.get(self.current.weather, {})
        for attr, (op, value) in modifiers.items():
            if attr in self.current.effects:
                continue  # 已应用, 不重复叠加
            original = player.get(attr, 0)
            self.current.effects[attr] = original
            if op == "mul":
                player[attr] = original * value
            elif op == "add":
                player[attr] = original + value

    def remove_effects(self, player):
        for attr, original in self.current.effects.items():
            player[attr] = original  # 逆操作: 恢复应用前的原值
        self.current.effects.clear()

    # ---- 阴影: 脏标记 + 阈值 + 分帧更新 ----
    def update_lighting(self):
        color = self.get_light_color()
        if self._last_light_color is None:
            self._last_light_color = list(color)
            return
        delta = max(abs(a - b) for a, b in zip(color, self._last_light_color))
        if delta > self.light_threshold:
            self.light_dirty = True
            self._shadow_chunks_done = 0
            self._last_light_color = list(color)

    def update_shadows(self):
        if not self.light_dirty:
            return "clean"
        self._shadow_chunks_done += 1  # 每帧只重算一批
        if self._shadow_chunks_done >= self.shadow_chunks:
            self.light_dirty = False
            self._shadow_chunks_done = 0
            return "recalculated"
        return "partial"

    # ---- 天空颜色: 按生物群系关键帧插值 ----
    def set_biome(self, biome):
        self.biome = biome

    def set_biome_colors(self, biome, colors):
        self.biome_colors[biome] = {n: list(c) for n, c in colors.items()}

    def get_sky_color(self):
        keyframes = self.biome_colors.get(self.biome, self.biome_colors["plains"])
        points = sorted((KEYFRAME_TIMES[name], color)
                        for name, color in keyframes.items()
                        if name in KEYFRAME_TIMES)
        if not points:
            return [0.5, 0.7, 1.0]
        t = (self.game_time / self.day_length) % 1.0
        # 找 t 所在的相邻关键帧区间, 末尾回绕到午夜
        for i, (t0, c0) in enumerate(points):
            t1, c1 = points[(i + 1) % len(points)]
            end = t1 if t1 > t0 else t1 + 1.0
            tt = t if t >= t0 else t + 1.0
            if t0 <= tt <= end:
                span = end - t0
                f = 0.0 if span == 0 else (tt - t0) / span
                if f <= 0.0:
                    return list(c0)
                if f >= 1.0:
                    return list(c1)
                return _lerp_color(c0, c1, f)
        return list(points[0][1])
