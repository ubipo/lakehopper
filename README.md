# Lakehopper 🐝🏞️

**Website:** [lakehopper.pfiers.net](https://lakehopper.pfiers.net)

Lakehopper is my long-term project to create a solar-powered autonomous drone
that rests on lakes during nights and overcast days. Think of it as a migrating
bird that survives off of photosynthesis.

{include-in-output}`/dissertation.pdf` As my [Master’s
thesis](/dissertation.pdf), I developed Lakehopper’s high-level planning
software. This system uses a convolutional neural network to identify lakes and
buildings from aerial imagery. From this, it generates a navigation graph to
calculate the best multi-hop paths between lakes. These paths avoid build-up
areas and restricted airspace. 

In my free time I’m working on the hardware of the drone. The [first
version](/design/1/README.md) I developed unfortunately experienced a
<s>crash</s>[rapid unscheduled disassembly](https://youtu.be/bvim4rsNHkQ) on its
maiden flight. I’m currently working on the [second
version](/design/2/README.md).



## High-Level Planning Software

You can find the training code and data pipeline for Lakehopper's machine vision
model in the [vision](/vision/README.md) folder. The
[planner](/planner/README.md) folder contains the source code for the planner
component.


## Lakehopper 1

Read about the design and maiden flight here: [Lakehopper 1
Design](/design/1/README.md).

![Lakehopper 1 on a workbench](/design/1/lakehopper-ground.webp)


## Lakehopper 2

I'm still hard at work on [Lakehopper 2's](/design/2/README.md) design and development.

In the meantime, here's what Lakehopper 2 will *probably* look like:

![Lakehopper 2 design preview](/design/2/preview.png)

<!-- ## Milestones

### MAV

The first milestone is to build a flying MAV.


### Lake hopping

Lake hopping involves:
- Waterproofing
- Water landings
- Water takeoffs


### Solar power

'Solar power' in my context means endless flight with breaks when necessary.

A plane that needs to charge for a week and can then do a two hour flight would
not be ideal but still pass. My ideal power generation graph however would 
probably look something like this:


### Autonomy

The autonomy milestone can be subdivided into automatic flight,
water landings and takeoffs, and navigation.

I will not be implementing automatic flight myself. This will be handled by the
[Ardupilot](https://ardupilot.org) autopilot software. 


 -->
