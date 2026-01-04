# homebatteryremote

Remote control and energy tracking / trading web app for the homebattery controller.

## Introduction

This repository is part of the [homebattery project](https://github.com/danielringch/homebattery). This app enabled users to control their homebattery controllers from everywhere using a simple web app.

homebatteryremote can:

- set the mode of operation of a homebattery setup either manually or based on a schedule
- show dynamic energy price data in the schedule editor, supported are:
  - tibber
- write energy cost/ revenue statistics to a csv file
- reset homebattery controllers

## Users and roles

There are three roles for using this app:

- the **operator** is the one with access to the machine the app is running on. The operator manages the connection to the MQTT broker and can influence which settings can be changed by the admin.
- the **admin** has access to the full web app, including the settings tab
- the **user** has access to the web app, but not to the settings tab

homebatteryremote is prepared to be provided as software-as-a-service, where the MQTT broker and homebatteryremote are operated by a service provider and the user of homebatteryremote has still admin access to all parts relevant for them.

## Configuration

There are two layers of configuration:

- the static configuration is done via yaml file and/ or environment variables
- the dynamic configuration can be done via the web app settings tab and is stored as a json file in the data directory.

Everything set in the static configuration gets readonly in the dynamic configuration, so the operator role can control what the admin role is able to change.

For keys in the static configuration that contain hashed or encrypted values:

- set them as admin role in the settings tab
- cut the value from the dynamic configuration json file
- paste it into the static configuration yaml file
- restart the app

An example file for the static configuration can be found in [config/sample.yaml](config/sample.yaml)

| Key  | Rules | Explanation |
| -- | -- | -- |
| ``data_dir``                                                      | string           | Path to directory used for application data. |
| ``name``                                                          | string           | Instance name. Will be shown as part of the login screen. |
| ``secret``                                                        | string           | Secret for encrypting passwords and securing user sessions. |
| ``log``<br>-> ``level``                                           | string           | Selected log level, allowed values: ``DEBUG``, ``INFO``, ``WARN``, ``ERROR`` or ``CRITICAL``. |
| ``log``<br>-> ``path``                                            | string           | Enables logging to file; path to log file. |
| ``log``<br>-> ``days``                                            | optional, int    | If set, log files are deleted after the given number of days. |
| ``mqtt``<br>-> ``host``                                           | string           | Host and port of the MQTT server; format: ``<host>:<port>``. |
| ``mqtt``<br>-> ``ca``                                             | optional, string | Enables TLS encryption; path to the TLS public certificate chain file. |
| ``mqtt``<br>-> ``tls_insecure``                                   | optional, bool   | Enables TLS encryption; but the TLS certificates are not checked (not recommended). |
| ``mqtt``<br>-> ``user``                                           | string           | The user name for log in to the MQTT server. |
| ``mqtt``<br>-> ``password``                                       | string           | The password for log in to the MQTT server. |
| ``homebattery``<br>-> ``<shown name>``<br>-> ``root``             | string           | MQTT root topic of the controller. |
| ``homebattery``<br>-> ``<shown name>``<br>-> ``is_mode_settable`` | string           | If set to true, the mode of operation for this controller can be written by this app. |
| ``homebattery``<br>-> ``<shown name>``<br>-> ``is_resettable``    | string           | If set to true, the controller can be reset by this app. |
| ``web``<br>-> ``listen``                                          | string           | IP address the webserver listens to. |
| ``web``<br>-> ``port``                                            | int              | Port the webservers listens to. |
| ``web``<br>-> ``admin_user``                                      | optional, string | User name of the admin role, default: ``admin``. |
| ``web``<br>-> ``admin_password``                                  | optional, string | Password hash of the admin role. |
| ``web``<br>-> ``user_user``                                       | optional, string | User name of the user role, default: ``user``. |
| ``web``<br>-> ``user_password``                                   | optional, string | Password hash of the user role. |
| ``web``<br>-> ``keyfile``                                         | optional, string | Enables HTTPS; path to TLS certificate private key. |
| ``web``<br>-> ``certfile``                                        | optional, string | Enables HTTPS; path to TLS certificate public key. |
| ``energy``<br>-> ``charger_efficiency_factor``                    | optional, float  | Efficiency of the connected chargers; range: ``0.0`` - ``1.0``; default: ``1.0``. |
| ``energy``<br>-> ``inverter_efficiency_factor``                   | optional, float  | Efficiency of the connected inverters; range: ``0.0`` - ``1.0``; default: ``1.0``. |
| ``energy``<br>-> ``minimum_margin``                               | optional, float  | Minimum margin to suggest charging/ discharging in the scheduler; unit: ``€``; default: ``0.00``. |
| ``energy``<br>-> ``csv_file``                                     | optional, string | Enables writing cost/ revenue statistics; path to csv file. |
| ``tibber``<br>-> ``token``                                        | optional, string | Encrypted tibber token. |

The following keys can alternatively be set using evironment variables:

| Key | Environment variable |
| -- | -- |
| ``data_dir``                  | ``HBRE_DATA_DIR`` |
| ``name``                      | ``BHRE_NAME`` |
| ``secret``                    | ``HBRE_SECRET`` |
| ``mqtt`` -> ``host``          | ``HBRE_MQTT_HOST`` |
| ``mqtt`` -> ``user``          | ``HBRE_MQTT_USER`` |
| ``mqtt`` -> ``password``      | ``HBRE_MQTT_PASS`` |
| ``web`` -> ``admin_user``     | ``HBRE_ADMIN_USER`` |
| ``web`` -> ``admin_password`` | ``HBRE_ADMIN_PASSWORD`` |
| ``web`` -> ``user_user``      | ``HBRE_USER_USER`` |
| ``web`` -> ``user_password``  | ``HBRE_USER_PASSWORD`` |
| ``tibber`` -> ``token``       | ``HBRE_TIBBER_TOKEN`` |


The following keys can alternatively be set in the dynamic configuration:

- ``web`` -> ``admin_user``
- ``web`` -> ``admin_password``
- ``web`` -> ``user_user``
- ``web`` -> ``user_password``
- ``energy`` -> ``charger_efficiency_factor``
- ``energy`` -> ``inverter_efficiency_factor``
- ``energy``-> ``minimum_margin``
- ``tibber`` -> ``token``

## First run

**Both passwords for admin and user must be set before exposing the app to public access.**

The passwords for admin and user are empty when running the app for the first time. Log in as admin (with an empty password) and set both passwords in the settings tab.

## Usage without docker

### Prerequisites

- Python 3 with pip + venv

This program should run on any OS, but I have no capacity to test this, so feedback is appreciated. My test machines run Ubuntu and Raspbian.

### Install

```
git clone https://github.com/danielringch/homebatteryremote.git
python3 -m venv <path to virtual environment>
source <path to virtual environment>/bin/activate
python3 -m pip install -r requirements.txt
```

### Run

```
source <path to virtual environment>/bin/activate
python3 -B src/homebatteryremote.py --config /path/to/your/config/file.yaml
```

## Usage with docker

TBD

## Get support

You have trouble getting started? Something does not work as expected? You have some suggestions or thoughts? Please let me know.

Feel free to open an issue here on github or contact me on reddit: [3lr1ng0](https://www.reddit.com/user/3lr1ng0).
