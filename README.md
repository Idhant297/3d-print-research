# 3d printer power data collection

steps to step up evrything for collecting data
-

1. stepup the kasa 125m smart plug using the mobile app. (https://apps.apple.com/us/app/kasa-smart/id1034035493)
2. step up the bambu labs printer. 
    > **Note:** step up both the printer and the smart plug on the same network. also the laptop that you will be using to collect the data.

3. clone this repo 
    ```sh
    git clone https://github.com/Idhant297/3d-print-research.git
    ```

4. install the required packages
    ```sh
    pip install -r requirements.txt
    ```

5. create a file `.env` and copy the contents from `sample.env` and add fill in the correct values into the variables.
    > also check the ip after every few time (or whenever it gives you an error) sometime the ip of the printer or the smart plug changes. you can check the ip of the printer from the printer itself and the ip of the smart plug from the kasa app.

### setup is complete!

other important instructions:
- 
1. switch the printer to **LAN only mode** from the netowkr settings in the printer. otherwise, the `bambu-mqtt.py` will not be able to connect to the printer.
2. make sure to start running the `bambu-mqtt.py` then `power.py` then start printing
    > only for the first time make a folder called `data`
3. whenever done with the print just commit that csv and json file into the repo (for the time being we storing the data in this repo only)
4. also whenver you print something save the gocode file also in the data folder with the same name as the csv and json file.
    > format will be `power_data_%Y-%m-%d_%H.%M.csv` you just copy the name from the csv and rename your `.gcode` file. \
    \
    eg: `power_data_2024-11-05_18.37.csv`, `power_data_2024-11-05_18.37_summary.json`, and `power_data_2024-11-05_18.37.gcode`
