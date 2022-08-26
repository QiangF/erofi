#!/usr/bin/python
# requires python-xlib

import re
import subprocess
import argparse
import os
import pickle
from sys import exit
from datetime import datetime
from Xlib import X, display
from time import sleep
import ewmh

def notify(string):
    runCommand(["notify-send", string])

def runCommand(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception("could not run command: {}\nresult: {}".format(command, result))
    return(result.stdout.decode("utf8"))

def unmaximize(win):
    ewmh.setWmState(win, 0, "_NET_WM_STATE_MAXIMIZED_VERT")
    ewmh.setWmState(win, 0, "_NET_WM_STATE_MAXIMIZED_HORZ")
    ewmh.setWmState(win, 0, "_NET_WM_STATE_FULLSCREEN")

def restoreLayout(savedGeos):
    activeGeos = getWindows()
    activeWids = [geo[0] for geo in activeGeos]
    savedWids = [geo[0] for geo in savedGeos]
    matchedWids = set(activeWids).intersection(set(savedWids))
    matchedGeos = []
    unmatchedGeos = []
    widsToUnhide = []
    for geo in activeGeos:
        wid = geo[0]
        win = ewmh.display.create_resource_object('window', wid)
        if wid in matchedWids:
            matchedGeos.append(geo)
        else:
            unmatchedGeos.append(geo)
        if '_NET_WM_STATE_HIDDEN' in ewmh.getWmState(win, True):
            widsToUnhide.append(wid)
    geosToResize = list(set(savedGeos).difference(set(matchedGeos)))
    # hide unmatched windows, which interferes with layout (visible windows) test
    for geo in unmatchedGeos:
        wid, x, y, w, h, wmclass = geo
        win = ewmh.display.create_resource_object('window', wid)
        ewmh.setWmState(win, 1, '_NET_WM_STATE_HIDDEN')
    for geo in savedGeos:
        wid, x, y, w, h, wmclass = geo
        if wid in matchedWids:
            win = ewmh.display.create_resource_object('window', wid)
            desktop = ewmh.getWmDesktop(win)
            if desktop != currentDesktop:
                # bring window on other desktop to current desktop
                ewmh.setWmDesktop(win, currentDesktop)
            if wid in widsToUnhide:
                ewmh.setWmState(win, 0, '_NET_WM_STATE_HIDDEN')
            if geo in geosToResize:
                wid, x, y, w, h, wmclass = geo
                win = ewmh.display.create_resource_object('window', wid)
                unmaximize(win)
                # move resize window
                win.configure(x=x, y=y, width=w, height=h)
            win.configure(stack_mode=X.Above)
    # set the input focus
    ewmh.setActiveWindow(win)
    ewmh.display.flush()

def getWindows(currentDesktopOnly=False, save=False):
    wins = ewmh.getClientListStacking()
    filteredWins = []
    for win in wins:
        desktop = ewmh.getWmDesktop(win)
        if currentDesktopOnly and desktop != currentDesktop:
            continue
        # remove invisible win
        if win.get_attributes().map_state == X.IsUnviewable:
            continue
        if save:
            # remove hidden win
            if '_NET_WM_STATE_HIDDEN' in ewmh.getWmState(win, True):
                continue
        if win.get_wm_class()[1] in set(['Tint2', 'Polybar', 'VirtualBox Machine']):
            continue
        filteredWins += [win]
    geos = []
    # gather geometry of all windows in higher zorder / possibly lying on top
    for win in filteredWins:
        parent_geometry = win.query_tree().parent.get_geometry()
        geometry = win.get_geometry()
        # x = parent_geometry.x - geometry.x
        # y = parent_geometry.y - geometry.y
        # frame border padding by window manager
        left, right, top, bottom = ewmh.getFrameExtents(win)
        w = geometry.width # + left + right
        h = geometry.height # + top + bottom
        x = parent_geometry.x # - left
        y = parent_geometry.y # - top
        geos += [(win.id, x, y, w, h, win.get_wm_class())]
    return geos

# layout functions
def setFileMtime(file_path, dt):
    dtEpoch = dt.timestamp()
    # times is a tuple (atime, mtime) in second
    os.utime(file_path, (dtEpoch, dtEpoch))

def getLayoutPath(time):
    return os.path.join(layoutDir, str(round(time.timestamp())))

def saveWindows(filename, windows):
    # Don't save empty layout.
    if len(windows) > 0:
        with open(os.path.join(layoutDir, filename), mode="wb") as b:
            pickle.dump(windows, b)

def loadWindows(filename):
    with open(os.path.join(layoutDir, filename), mode='rb') as b:
        return(pickle.load(b))

def winner(i, layoutFiles):
    filesByMtimeAscending = sorted(layoutFiles, key=lambda t: os.stat(os.path.join(layoutDir, t)).st_mtime)
    lastAccessedFilename = filesByMtimeAscending[-1]
    if (now.timestamp() - lastRunTime) > checkPeriod:
        newRun = True
        period = (now.timestamp() - lastRunTime)
        # rename last accessed file, make sure the more used layoutFiles are closer to the tip
        os.rename(os.path.join(layoutDir, lastAccessedFilename), getLayoutPath(now))
        lastAccessedFilename = str(round(now.timestamp()))
    else:
        newRun = False
    # update layoutFiles
    layoutFiles = os.listdir(layoutDir)
    filesByNameAscending = sorted(layoutFiles)
    lastAccessedLayoutIndex = filesByNameAscending.index(lastAccessedFilename)
    # in a continuous run
    if newRun:
        # forward
        if i > 0:
            fileID = i - 1
        else:
            lastGeos = loadWindows(lastAccessedFilename)
            if lastGeos == currentGeos:
                fileID = i - 1
            else:
                fileID = i
    else:
        fileID = lastAccessedLayoutIndex + i
    fileID %= len(layoutFiles)
    filename = filesByNameAscending[fileID]
    savedGeos = loadWindows(filename)
    if (not savedGeos == currentGeos):
        restoreLayout(savedGeos)
    else:
        notify("Same layouts!")
    # change mtime of filename to current time
    setFileMtime(os.path.join(layoutDir, filename), now)
    return

def newLayout(layoutFiles):
    filesByNameAscending = sorted(layoutFiles)
    isNew = True
    for f in layoutFiles:
        if set(loadWindows(f)) == set(currentGeos):
            # no duplicate layout
            os.rename(f, getLayoutPath(now))
            return
    filename = getLayoutPath(now)
    saveWindows(filename, currentGeos)
    if layoutNumber == maxLayoutNumber:
        os.remove(os.path.join(layoutDir, filesByNameAscending[0]))
    notify("New layout!")

ewmh = ewmh.EWMH()
if ewmh.getShowingDesktop() == 1:
    ewmh.setShowingDesktop(0)
currentDesktop = ewmh.getCurrentDesktop()
layoutDir = os.path.join("/tmp/window-layout/", os.environ["USER"], str(currentDesktop))
now = datetime.now()
checkPeriod = 5
if os.path.isdir(layoutDir):
    lastRunTime = os.stat(layoutDir).st_mtime
    # set layoutDir mtime to be the last run time
    setFileMtime(layoutDir, now)
else:
    os.makedirs(layoutDir, exist_ok=True)
layoutFiles = os.listdir(layoutDir)
layoutNumber = len(layoutFiles)
maxLayoutNumber = 8
currentGeos = getWindows(True, True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Save and load window layouts")
    parser.add_argument("operation", metavar="[next|last|new]", type=str, nargs=1,
                        help="next, previous,  new (create new layout)")
    args = parser.parse_args()
    op = args.operation[0]
    if op == "new":
        newLayout(layoutFiles)
    else:
        if layoutNumber == 0:
            newLayout(layoutFiles)
        else:
            if op == "next":
                winner(1, layoutFiles)
            elif op == "last":
                winner(-1, layoutFiles)
            else:
                raise Exception("unknown operation: " + op)
