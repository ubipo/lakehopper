# Lakehopper 1 Design

Have a look at the notebooks for each iteration of Lakehopper 1's design:

- [Iteration 1: Aspect Ration](iteration_1_ar.ipynb)
- [Iteration 2: Weight and Airfoil](iteration_2_weight_and_airfoil.ipynb)
- [Iteration 3: Propulsion](iteration_3_propulsion.ipynb)
- [Iteration 4: Propulsion Weight](iteration_4_propulsion_weight.ipynb)
- [Iteration 5: FPV Weight](iteration_5_fpv_weight.ipynb)
- [Iteration 6: Stability](iteration_6_stability.ipynb)

This iterative approach is inspired by [Carlos Montalvo's *Aircraft Flight Mechanics*](https://github.com/cmontalvo251/LaTeX/blob/master/Aircraft_Flight_Mechanics/Aircraft_Flight_Mechanics.pdf).

![Lakehopper 1 on a workbench](lakehopper-ground.webp)

## Maiden Flight

Lakehopper 1 took its maiden flight on monday the 6th of September 2021.
Unfortunately she only flew for about 3 seconds before crashing sideways and
breaking her wing with a *crack*.

{include-in-output}`maiden.mp4`

<video width="100%" controls>
  <source src="maiden.mp4" type="video/mp4">
</video>

While I plan to write a full post-mortem some time in the future, in short: the flight
controller was misconfigured and thought the plane was facing left, which caused
the sharp bank to the right.

{include-in-output}`v1-maiden-6-9-21.bin`
You can view the flight log in the [Ardupilot UAV Log
Viewer](https://plot.ardupilot.org/) by loading
[v1-maiden-6-9-21.bin](v1-maiden-6-9-21.bin). The screenshot below shows the
most important part of this log: the incorrect orientation as well as the flight
controller's incorrect roll and pitch measurements.

![Log of Lakehopper 1's maiden flight](maiden-log-view.png)
