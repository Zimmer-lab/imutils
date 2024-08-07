# it is very slow somehow. I do not think it is correct

# function to animate worm track
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd

# define writer
Writer = animation.writers['ffmpeg']
writer = Writer(fps=103, metadata=dict(artist='Me'), bitrate=1800)

plt.style.use('seaborn-talk')

fig = plt.figure()
ax = plt.axes()
ax.set_xlim([-15, 5])
ax.set_ylim([-4, 4])
line_track, = ax.plot([], [], lw=1, c='gray')
line, = ax.plot([], [], markersize=6,  marker='o', c='black')
line_rev, = ax.plot([], [], marker='o', markersize=6, c='red')

# load data
path = '/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/worm3/2021-03-04_16-17-30_worm3_ZIM2051-TablePosRecord.txt'
df = pd.read_csv(path)
beh_path='/Volumes/scratch/neurobiology/zimmer/ulises/wbfm/worm3/beh_annotation_16_subsamples_timeseries.csv'
beh=pd.read_csv(beh_path)

# lists to store x and y axis points
xdata = df['X']  # df['x_head_corrected']
ydata = df['Y']  # df['y_head_corrected']

initial_time = 0

color_dict = {'forward': u'blue',
              'reversal': u'red',
              'sustained reversal': u'red',
              'ventral turn': u'blue',
              'dorsal turn': u'blue'}

# initialization function
def init():
    # creating an empty plot/frame
    line.set_data([], [])
    return line,

# animation function
def animate(i):
    # t is a parameter
    t = initial_time + i * 16#16
    print(t)
    # print(beh.loc[i,'state']=='reversal')
    # print('y data', ydata[t])
    # print('x data', xdata[t])
    #ax.scatter(xdata[t], ydata[t], lw=0.5, c=beh['state'].map(color_dict)[t/16], s=3)

    if beh.loc[i,'state'] == 'reversal':
        print('reversal')
        line_rev.set_data(xdata[t-350:t], ydata[t-350:t])
        line.set_data([], [])
    if beh.loc[i,'state'] != 'reversal':
        print('forward')
        line.set_data(xdata[t-350:t], ydata[t-350:t])
        line_rev.set_data([], [])

    #plot track
    line_track.set_data(xdata[0:t], ydata[0:t])

    return line, line_rev, line_track


# setting a title for the plot
#plt.title('Worm trajectory')
# hiding the axis details
plt.axis('off')

# call the animator
anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=3131, interval=1, blit=True)
#plt.show()
anim.save('worm3_tracks_black_annotated_103fps.mp4', writer=writer)