from math import ceil, log
import statistics as stats
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches
import numpy as np

AREAS = [500, 1500, 2000, 2500, 3000, 3400, 3500]
NBRO_VERTICES = [54, 516, 836, 1303, 1728, 2206, 2711]
APPROXIMATIONS = [lambda n: (n/41)**3, lambda n: ((n/24)**2)*log(n/24), lambda n: ((n/30)**2)*log(n/30)]
MODES = ['Naive: $O(n^3)$', 'Sweep: $O(n^2\log(n))$', 'Optimized: $O(n^2\log(n))$']
MARKERS = ['o', 'v', 's']
COLORS = ['c', 'y', 'm']
RUNS = [
    [
        [13, 17, 21, 29, 27, 25, 25, 28, 25, 26],
        [41, 39, 35, 31, 27, 26, 26, 29, 28, 27],
        [26, 15, 22, 21, 19, 20, 22, 23, 20, 20],
    ],
    [
        [3236, 2397, 2131, 2048, 2063, 2054, 2046, 2066, 2052, 2059],
        [1479, 1352, 1380, 1328, 1336, 1269, 1317, 1290, 1314, 1272],
        [856, 811, 939, 880, 815, 739, 821, 869, 719, 692],
    ],
    [
        [8633, 8029, 7393, 7419, 7564, 7623, 7330, 7396, 7291, 7285],
        [3896, 3801, 3520, 3554, 3632, 3467, 3453, 3732, 3560, 3478],
        [2912, 2836, 2204, 1968, 2100, 2163, 1975, 2092, 2044, 2205]
    ],
    [
        [25861, 25691, 29760, 29036, 29032, 29870, 29084, 32891, 31129, 29165],
        [9469, 8651, 8596, 8581, 8769, 8971, 9335, 9211, 8939, 8751],
        [6054, 5599, 5293, 5351, 5669, 5591, 5738, 6457, 5983, 5443],
    ],
    [
        [57120, 58351, 59029, 70939, 77569, 76131, 66510, 63310, 65546, 61425],
        [16547, 15401, 15236, 15232, 15504, 15674, 15604, 15523, 15510, 15685],
        [9951, 9426, 9446, 9450, 9465, 9472, 9485, 9483, 9549, 9610]
    ],
    # 3250 (n=2006)
    # [
    #     [89945, 86709, 91286, 92470, 95983, 89671, 93410, 93395, 90920, 91316],
    #     [23393, 21202, 21059, 24658, 20907, 24588, 24626, 20833, 24580, 24691],
    #     [13186, 13118, 13150, 13143, 13349, 13425, 13405, 13448, 13474, 13586]
    # ],
    [
        [121624, 116231, 116005, 116119, 116111, 115842, 116585, 116171, 115901, 116197],
        [27550, 25938, 25600, 25919, 25876, 26112, 26010, 25876, 25964, 25862],
        [17498, 16489, 16561, 16790, 18515, 18107, 18480, 17852, 20061, 19508]
    ],
    [
        [220898, 242354, 244913, 244505, 249334, 249770, 237215, 242430, 242019, 243516],
        [41820, 56791, 50968, 55234, 56390, 53421, 57679, 58941, 49302, 56217],
        [29402, 37206, 35276, 31934, 35358, 29995, 35212, 35223, 37961, 35332],
    ]
]

runs_by_mode = zip(*RUNS)

fig = plt.figure()
ax1 = fig.add_subplot(111)

# ax1.set_title('Running time of visibility graph algorithms')
ax1.set_xlabel('No. of vertices in visibility graph')
ax1.set_ylabel('Running time ($s$)')

for mode_i, (mode, runs, marker, color, approximation) in enumerate(zip(MODES, runs_by_mode, MARKERS, COLORS, APPROXIMATIONS)):
    runs_s = [[time_ms/1000 for time_ms in run] for run in runs]
    means = [stats.mean(run) for run in runs_s]
    std_devs = [np.std(run) for run in runs_s]
    ax1.errorbar(NBRO_VERTICES, means, yerr=std_devs, c=color, marker=marker, label=mode)

    approximation_range = (min(NBRO_VERTICES), max(NBRO_VERTICES))
    approximation_xs = list(range(*approximation_range, int((approximation_range[1]-approximation_range[0])/100)))
    approximation_ys = [approximation(x)/1000 for x in approximation_xs]

    ax1.plot(approximation_xs, approximation_ys, color=color, marker=',', linestyle=':')

handles, labels = plt.gca().get_legend_handles_labels()
big_o_legend_line = Line2D([0], [0], label='Big O bound', color='k', linestyle=':')
handles.extend([big_o_legend_line])

plt.legend(loc='upper left', handles=handles);
plt.show()

# plt.scatter()
