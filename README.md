# README

# Agent
## Refactor:
this local variables are breaking our code, its too huge so i cant maintain, we need to decompose the monolithic structure into modular one;

read the SYNC.sh file and plan a way to split into modules;

we can think using python instead bash if its faster, or concise, we are using bash because workthisout uses bash, but it calls a lot of python code;

workthisout.sh is inside ./source/

workthisout.sh is the main script of our SYNC.sh function, everything we are doing if to make the terrain to execute workthisout with --luke mode and sincronize our ./sds/ to the server /SDS/ and then use index.sh to start analyzing our data;

[1]: https://github.com/Gabriel-Goes/Pre-Sync/pull/6 "Refine documentation cross-links and add Furo theme options by Gabriel-Goes · Pull Request #6 · Gabriel-Goes/Pre-Sync · GitHub"

## RT130 Logger

### Parametros observados no arquivo:
    SH = State of Health
    SC = Station Channel Definition
    OM = Operating Mode Definition
    DS = Data Stream Definition
    AD = Auxiliary Data Parameter
    CD = Calibration Definition
    FD = Filter Description
    EH = Event Header
    ET = Event Trailer

