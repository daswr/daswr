import daswr,signal,json,argparse,sys,time



APP_PIDS=None
MIC_ID=None
OUT_ID=None


PARSER = argparse.ArgumentParser(description='Process some integers.')

PARSER.add_argument('--pids', metavar='N', type=int, nargs='+',help='Pids of the processes to stream')
PARSER.add_argument('--voice-in', type=str,help='Name of the voice source. Default: auto=guess the default voice in')
PARSER.add_argument('--output', type=str,help='Output sink for the mixed audio. Default: auto=guess the default audio output')
aa=PARSER.parse_args()



APP_PIDS=aa.pids if aa.pids else daswr.selectProcessesWithClick()
MIC_ID=aa.voice_in
OUT_ID=aa.output
STOP=False

if not MIC_ID: MIC_ID=daswr.listSources()[0]["name"]
if not OUT_ID:OUT_ID=daswr.listSinks()[0]["name"]


def load():
    try:
        with open('daswr-cli.json', 'r') as f:    
            data = json.load(f)
    except:
        return []

def save(data):
    with open('daswr-cli.json', 'w') as f:
        json.dump(data, f)

def sigint_handler(sig,frame):
    global STOP
    STOP=True
    print("Prepare to close...")



print("Use input source",MIC_ID)
print("Use output ",OUT_ID)
print("Stream app",APP_PIDS)

signal.signal(signal.SIGINT, sigint_handler)

while not STOP:
    daswr.rewire(MIC_ID,APP_PIDS,OUT_ID,[load,save])
    time.sleep(1)

daswr.cleanup()
print("Closed.")