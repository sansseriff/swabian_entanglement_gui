# High Rate Entanglement PySide2 Software

1. Install the [swabian timetagger software](https://www.swabianinstruments.com/time-tagger/downloads/)
    - On redhat, navitage to the location of the file and install with:
    ```
    sudo yum install name-of-timetagger-file.rpm
    ```
    - The example files are located in ``` /lib64/timetagger ```
    - The installtion will put some timetagger specific files in the site-packages folder of one of the computer's python installations. You will need to find them. You can try looking in folders like these, change ```python3.6``` to the default verion on the system.
    ```
    /usr/lib/python3.6/site-packages/
    /usr/lib64/python3.6/site-packages/
    ```

    The files (as of Timetagger sofware version 2.13.2) include: 
    ```shell
    TimeTagger.py
    _TimeTagger.cxx
    _TimeTagger.h
    _TimeTagger.so
    ```

    Note down the path to these files, and save for later. I'll call this ```<default-python-path>```
    

2. Using anaconda, run the following in shell: 
```shell
conda env create -f environment.yaml
```

3. After that is finished, activate the environment:
```shell
conda activate entanglement
```

4. You will need to copy the files from step 1 into the new entanglement environment site-packages folder. With the ```entanglement``` environment activated, run the ```get_site_packages.py``` script and note the path in the output. I'll call this path ```<entanglement-path>```.

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

run the program with:
```shell
python entanglement_analysis.py
```

Hit the "Load File Params" button first, then the "Clock Referenced Mode" button to activate the PLL. 



# Notes

- Lower the count rate if you get an error similar to ```SWIG director method error. In method 'next_impl': ZeroDivisionError```