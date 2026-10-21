import jax

jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp
from difflow import Heater, HeaterParams, make_stream

feed = make_stream({"A": 4.0}, T=300.0, P=101325.0)


def heat_duty(T_out):
    heater = Heater(HeaterParams(T_out=T_out, Cp=80.0))
    outlet, info = heater(feed)
    return info["Q"]


target = jnp.array(350.0)
duty = heat_duty(target)
sensitivity = jax.grad(heat_duty)(target)

print(f"Heat duty: {float(duty) / 1000:.3f} kW")
print(f"dQ/dT_out: {float(sensitivity):.3f} W/K")