#SliceAnim.py

import maya.cmds as mc
import functools


#to place a slice in the right collection of parts based on y value
#attribs: part's minimum y, part's maximum y, slice height array
#returns: the position at which the part should be placed
def place(pym, pyM, pSht):
    pos = -1
    for i in range(1,len(pSht)):
        pos = i
        if(pyM <= pSht[i] and pym>= pSht[i-1]):
            #debug
            #print pSht[i-1], ' <= ', pym, ' <= ', pyM, ' <= ', pSht[i]
            break
    return pos-1
        
#for defining and displaying UI
#attribs: title of the window, apply callback function
#returns: nothing
#TODO   : make fields for start time and end time and also the target attribute
def createUI(pWindowTitle, pApply):
    winID = 'slicer'
    
    if(mc.window(winID, exists = True)):
        mc.deleteUI(winID)
    
    #define the window and its attributes
    mc.window(winID, title = 'slicer', sizeable = False, resizeToFitChildren = True)    
    mc.rowColumnLayout(numberOfColumns = 3, columnWidth = [[1,100],[2,60],[3,60]], columnOffset = [[1,'right',3]])
    
    #row 1
    mc.text('Number of Slices:')
    numCuts = mc.intField(value = 0)
    mc.separator(height = 10, style = 'none')
    
    #row 2
    mc.text('Time (frames):')
    time = mc.intField(value = 10)
    mc.separator(height = 10, style = 'none')
    
    #cancel callback
    def cancel(*pArgs):
        if(mc.window(winID, exists = True)):
            mc.deleteUI(winID)
    
    #row 3
    mc.separator(height = 10, style = 'none')
    mc.button(label = 'Apply', command = functools.partial(pApply, numCuts,time))
    mc.button(label = 'Cancel',command = cancel)
    
    #display the window that was defined
    mc.showWindow()
    
#for animation
#attribs: object name, start time of animation, end time of animation
#         starting value of animation, ending value of animation,
#         target attribute of animation  
#returns: nothing
#TODO   : Maybe add parameters to change tangents as well?
def keyanim(pObjName, pStartTime, pEndTime, pStartVal, pEndVal, pTargetAttrib):
    #to delete any existing keys for the target attribute in the given frame range
    mc.cutKey(pObjName, time = (pStartTime, pEndTime), attribute = pTargetAttrib)
    #to set a new key frame for the start of the animation
    mc.setKeyframe(pObjName, time = pStartTime, attribute = pTargetAttrib, value = pStartVal)
    #to set a new key frame for the end of the animation
    mc.setKeyframe(pObjName, time = pEndTime, attribute = pTargetAttrib, value = pEndVal)
    #to select the key and make it's tangents linear
    mc.selectKey(pObjName, time = (pStartTime, pEndTime), attribute = pTargetAttrib, keyframe = True)
    mc.keyTangent(inTangentType = 'linear', outTangentType = 'linear')    

#for animating slices of stuff
#attribs: array with slices, time to end the animation at (starts at 0)
#returns: nothing
#TODO   : generalize for any start time and end time.
def animateslices(pSlices, pTime):
    j = pSlices[0]
    #set the time interval between each slice's animation
    interval = int(pTime)/len(j)
    #debug
    #print j
    #print pTime
    #print interval
    
    #now animate each slice
    for k in range(len(j)):
         keyanim(j[k],interval*k, interval*(k+1),0,2,'translateX')   
        
        
#for slicing stuff
#attribs: the object that needs to be sliced, the number of slices required
#returns: list of parts obtained after running polyCut and polySeparate on the object.
#TODO   : Make it modular
def slicer(pObj, pNumCuts):
    bb = mc.exactWorldBoundingBox()
    ymin = bb[1]
    ymax = bb[4]

    ocx = mc.objectCenter(x = True)
    ocy = mc.objectCenter(y = True)
    ocz = mc.objectCenter(z = True)
    sliceht = [ymin]
    
    #Cut into parts, still same object
    for i in range(1,pNumCuts):
        sht = round(ymin+ i*((ymax-ymin)/pNumCuts), 2)
        mc.polyCut(pObj,
                   cutPlaneCenter = [ocx, sht, ocz],
                   cutPlaneRotate = [90,0,0],
                   extractFaces = True,
                   extractOffset = [0,0,0])
        sliceht.append(sht)
        
    #separate each part into different objects   
    objList = mc.polySeparate(pObj)
    sliceht.append(ymax)
    #to store the parts in each place - dictionary
    #index represents slice number
    places = {}

    #initialize each slice with an empty list
    for i in range(pNumCuts):
        places[i] = []

    partList = []
    i=0
    
    #close border and rename each part, and keep track of parts
    for part in objList:
        try:
            mc.polyCloseBorder(part)

            #get part's bounding box
            pbb = mc.polyEvaluate(part, b=True)
            
            #to see if bbox is returned or a message saying "Nothing is..." is returned
            if(pbb[0]!='N'):                
                mc.rename(part,'part'+str(i))
                
                #just need max/min y of part, so pbb[1] required
                #part's min y
                pm = round(pbb[1][0],2)
                #part's max y
                pM = round(pbb[1][1],2)
                #find which slice the part belongs to
                pl = place(pm,pM,sliceht)
                #add the new part to the places dictionary to the right slice
                places[pl].append('part'+str(i))
                i+=1
                
        except RuntimeError:
            break

    #combine parts at same slice level        
    for key in places:
        #if a slice has more than one part
        if(len(places[key])>1):
            #combine parts in slice numbered "key", name it something unique
            mc.polyUnite(*places[key], n = 'unite'+str(key))
            #initialize newpart to this newly created object
            newpart = 'unite'+str(key)
        #else there's no need for combining anything    
        else:
            newpart = places[key]
        
        #rename each new part to coll<key> where key is the slice number    
        mc.rename(newpart,'coll'+str(key))
        #add this new collection to the partList
        partList.append('coll'+str(key))
    
    return partList       

#to apply the given time range and number of slices to the given object
#attribs: Number of slices, time range for animation (these are the only attribs that matter, but *pArgs needs to be there)
#returns: nothing
#TODO   : Make changes when new fields are added to the UI
def apply(pNumCuts, pTime, *pArgs):
    numCuts = mc.intField(pNumCuts, query = True, value = True)
    time = mc.intField(pTime, query = True, value = True)
    sl = mc.ls(selection = True)
    parts = []
    for i in sl:
        parts.append(slicer(i,numCuts))
    animateslices(parts, time)

#actually create and display the UI        
createUI('Slicer',apply)