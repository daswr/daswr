import pulsectl,re

PULSE=pulsectl.Pulse('dasw') 
FIND_SINK_NAME_IN_ARGS_RE= re.compile('sink_name=([A-Z0-9_]+)', re.IGNORECASE)
FIND_SRC_IN_ARGS_RE= re.compile('source=([A-Z0-1_]+)\.monitor', re.IGNORECASE)
FIND_SINK_IN_ARGS_RE= re.compile('sink=([A-Z0-9_]+)', re.IGNORECASE)

# LOADED_MODULES=[]

def getSinkByName(name):
    sinks=PULSE.sink_list()
    for sink in sinks:
        if(sink.name==name):
            return sink
    return None

def findModuleIdBySinkName(name):
    for m in PULSE.module_list():
        a=m.argument
        if not a:continue
        sink_name_reo=FIND_SINK_NAME_IN_ARGS_RE.search(a)
        if not sink_name_reo: continue
        sink_name=sink_name_reo.group(1)
        if sink_name==name: return m.index
    return None


def findModuleIdBySourceAndSink(src,sink):
    for m in PULSE.module_list():
        a=m.argument
        if not a:continue
        sink_reo=FIND_SINK_IN_ARGS_RE.search(a)
        source_reo=FIND_SRC_IN_ARGS_RE.search(a)
        if not source_reo or not sink_reo: continue
        sink_name=sink_reo.group(1)
        source_name=source_reo.group(1)
        if sink_name==sink and source_name==src: return m.index
    return None

def deleteSinkByName(name):
    module_id=findModuleIdBySinkName(name)
    if not module_id:return
    print("Unload module",module_id)
    PULSE.module_unload(module_id)

def deleteLoopBackBySourceAndDest(src,dest):
    module_id=findModuleIdBySourceAndSink(src,dest)
    PULSE.module_unload(module_id)

def getOrCreateNullSink(name):
    sink=getSinkByName(name)
    if not sink:
        print(name,"doesn't exist. Create")
        PULSE.module_load("module-null-sink","sink_name="+name)
        # LOADED_MODULES.append(name)
        sink=getSinkByName(name)
    return sink
   

def getOrCreateLoopBack(src,dest):
    module_id=findModuleIdBySourceAndSink(src,dest)
    if not module_id:
        print(src,"-",dest,"not found. Create")
        module_id= PULSE.module_load("module-loopback","source="+src+".monitor sink="+dest)
    else:
        print("Found loopback at",module_id)
    return module_id


print("Start")
# print(findModuleIdBySinkName("Test"))

print(getOrCreateNullSink("Test1"))
print(getOrCreateNullSink("Test2"))
print(getOrCreateLoopBack("Test1","Test2"))
# for m in PULSE.source_list():
#     print(m)
deleteSinkByName("Test1")
deleteSinkByName("Test2")
deleteLoopBackBySourceAndDest("Test1","Test2")