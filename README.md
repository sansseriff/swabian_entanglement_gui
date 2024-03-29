# High Rate Entanglement PySide2 Software

This software is used measure coincidences and control the high rate entanglement experiment based on a fast mode locked laser. 

![entanglement_software_image](entanglement_software_img.png)

## Getting Started

1. In a directory of your choice, initialize a git repo and pull from this repo. 

```shell
git init
git pull https://github.com/sansseriff/swabian_entanglement_gui.git 
```

2. Install the [swabian timetagger software](https://www.swabianinstruments.com/time-tagger/downloads/)
    - On redhat, navigate to the location of the file and install with:
    ```
    sudo yum install name-of-timetagger-file.rpm
    ```
    - The example files are located in ``` /lib64/timetagger ```
    - The installation will put some timetagger specific files in the site-packages folder of one of the computer's python installations. You will need to find them. You can try looking in folders like these, change ```python3.6``` to the default version on the system.
    ```
    /usr/lib/python3.6/site-packages/
    /usr/lib64/python3.6/site-packages/
    ```

    The files (as of Timetagger software version 2.13.2) include: 
    ```shell
    TimeTagger.py
    _TimeTagger.cxx
    _TimeTagger.h
    _TimeTagger.so
    ```

    Note down the path to these files, and save for later. I'll call this ```<default-python-path>```
    

3. Using anaconda, run the following in shell: 
```shell
conda env create -f environment.yaml
```

4. After that is finished, activate the environment:
```shell
conda activate entanglement
```

5. You will need to copy the files from step 1 into the new entanglement environment site-packages folder. Activate the environment:
```shell
conda activate entanglement 
```
Then run the ```get_site_packages.py``` file to get the path to the correct site-packages folder. I'll call this path ```<entanglement-path>```.

Run the following commands, inserting the relevant paths. 

```shell
cd <default-python-path> 
sudo cp TimeTagger.py <entanglement-path> 
sudo cp _TimeTagger.cxx <entanglement-path>
sudo cp _TimeTagger.h <entanglement-path>
sudo cp _TimeTagger.so <entanglement-path>
```

Navigate back to the program directory: 
```shell
cd <entanglement-path>
```

To use the voltage source, you will need the SNSPD library installed, which has the Teledyne voltage source control scripts. See the [SNSPD wiki](http://10.7.0.104/git). Even if it's already installed, you will need to link it to the new `entanglement` environment. Run the script `activate_snspd.py` to do this linking. 

With the entanglement environment still activated, run the program with:
```shell
python entanglement_control.py
```

Select the `Load File Params` button first. Select the `Init VSource` button to connect to the Teledyne T3PS2303P voltage source. Then select the `Clock Referenced Mode` button to activate the PLL custom measurement. Each one of these activations may cause errors you will have to solve. The PLL will currently crash unless a valid clock signal is specified on channels C (and channel D for timetagger X in high res mode). 


There is an optional `-auto_init` argument. Use it like this:
```shell
python entanglement_control.py -auto_init
```
This loads the file params, connects to the voltage source, and runs the PLL immediately . This is not recommended during debugging because it can make it difficult to determine what module is causing the program to crash. 


## Notes and Tips

- Lower the count rate if you get an error similar to ```SWIG director method error. In method 'next_impl': ZeroDivisionError```

- The button for Clock Referenced Mode engages the the software defined PLL. After pressing this, select 'Zoom to Peak' to scan in time for the entangled photon pairs coincidence peak. This button should also center the largest time bin in the center of the histogram on the lower left. Note that it works better if the phase of the control interferometer is set so that the center bin has maximized count rate. 

- Some fields in the gui may not be used, like the saveName dialogue. You can hook into these gui features by customizing the code if you wish. (I often rename buttons in ```entanglement_control_window.py``` and re-assign them to point to different functions.)

- Remember to deactivate the environment if you are no longer using the program (or just close the terminal)