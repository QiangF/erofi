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

def unmaximize(win):
    ewmh.setWmState(win, 0, "_NET_WM_STATE_MAXIMIZED_VERT")
    ewmh.setWmState(win, 0, "_NET_WM_STATE_MAXIMIZED_HORZ")
    ewmh.setWmState(win, 0, "_NET_WM_STATE_FULLSCREEN")

def restoreLayout(savedGeos):
    allGeos = getWindows()
    allWids = [geo[0] for geo in allGeos]
    savedWids = [geo[0] for geo in savedGeos]
    matchedWids = set(allWids).intersection(set(savedWids))
    matchedGeos = []
    for geo in allGeos:
        if geo[0] in matchedWids:
            matchedGeos.append(geo)
    geosToResize = list(set(savedGeos).difference(set(matchedGeos)))
    for geo in savedGeos:
        wid, x, y, w, h, wmclass = geo
        if wid in matchedWids:
            win = ewmh.display.create_resource_object('window', wid)
            desktop = ewmh.getWmDesktop(win)
            if desktop != currentDesktop:
                # bring window on other desktop to current desktop
                ewmh.setWmDesktop(win, currentDesktop)
            if geo in geosToResize:
                wid, x, y, w, h, wmclass = geo
                win = ewmh.display.create_resource_object('window', wid)
                unmaximize(win)
                # move resize window
                win.configure(x=x, y=y, width=w, height=h)
            win.configure(stack_mode=X.Above)
    ewmh.display.sync()

def getWindows(currentDesktopOnly=False):
    wins = ewmh.getClientListStacking()
    filteredWins = []
    for win in wins:
        desktop = ewmh.getWmDesktop(win)
        if currentDesktopOnly and desktop != currentDesktop:
            continue
        # remove invisible win
        if win.get_attributes().map_state == X.IsUnviewable:
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
    # times is a tuple (atime, mtime)
    os.utime(file_path, (dtEpoch, dtEpoch))

def getLayoutPath(time):
    return os.path.join(layoutDir, str(round(time.timestamp())))

def saveWindows(filename, windows):
    with open(os.path.join(layoutDir, filename), mode="wb") as b:
        pickle.dump(windows, b)

def loadWindows(filename):
    with open(os.path.join(layoutDir, filename), mode='rb') as b:
        return(pickle.load(b))

def winner(i):
    filesByMtimeAscending = sorted(layoutFiles, key=lambda t: os.stat(os.path.join(layoutDir, t)).st_mtime)
    filesByNameAscending = sorted(layoutFiles)
    lastAccessedFilename = filesByMtimeAscending[-1]
    lastAccessedLayoutIndex = filesByNameAscending.index(lastAccessedFilename)
    newRun = False
    # in a continuous run
    if (abs(i) <= 1) and ((now.timestamp() - lastRunTime) < checkPeriod):
        fileID = lastAccessedLayoutIndex + i
    else:
        newRun = True
        fileID = i
    fileID %= len(layoutFiles)
    filename = filesByNameAscending[fileID]
    savedGeos = loadWindows(filename)
    if (not savedGeos == currentGeos):
        restoreLayout(savedGeos)
    # change mtime of filename to current time
    setFileMtime(os.path.join(layoutDir, filename), now)
    if newRun:
        # rename last accessed file, make sure the more used layoutFiles are closer to the tip
        os.rename(os.path.join(layoutDir, lastAccessedFilename), getLayoutPath(now))
    return

def newOrCycle(layoutFiles):
    if (now.timestamp() - lastRunTime) < checkPeriod:
        winner(-1)
    else:
        filesByNameAscending = sorted(layoutFiles)
        isNew = True
        for f in layoutFiles:
            if set(loadWindows(f)) == set(currentGeos):
                winner(-1)
                return
        filename = getLayoutPath(now)
        saveWindows(filename, currentGeos)
        if layoutNumber == maxLayoutNumber:
            os.remove(os.path.join(layoutDir, filesByNameAscending[0]))
            # skip the just added layout
            winner(-2)
        return

ewmh = ewmh.EWMH()
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
currentGeos = getWindows(True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Save and load window layouts")
    parser.add_argument("operation", metavar="[next|last|new]", type=str, nargs=1,
                        help="next, previous,  new (create new layout)")
    args = parser.parse_args()
    op = args.operation[0]
    if op == "new":
        newOrCycle(layoutFiles)
    else:
        if layoutNumber == 0:
            newOrCycle(layoutFiles)
        else:
            if op == "next":
                winner(1)
            elif op == "last":
                winner(-1)
            else:
                raise Exception("unknown operation: " + op)