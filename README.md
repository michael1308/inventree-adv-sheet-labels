# InvenTree Advanced Sheet Label Printing Plugin

Advanced sheet label printing plugin for InvenTree which adds more features to the included plugin including printing on off-the-shelf label paper layouts.


## Development setup

To develop the plugin, setup an InvenTree development instance using devcontainers according to this [this](https://docs.inventree.org/en/latest/develop/devcontainer/) official documentation. It is also recommended to setup the example dataset for experimenting.

Then clone this repo separately on your host computer and link it to the devserver in [this](https://docs.inventree.org/en/latest/develop/devcontainer/#plugin-development) way. 

It is also recommended to save the workspace as a file (maybe somewhere in inventree repo but don't commit it) and include the intellisenseconfig as well as editor layout there.

The InvenTree intellisense path might be something like  ```/home/inventree/src/backend/InvenTree``` instead of the path from the documentation.

After that, start the InvenTree server with the debugger and the plugin should now be usable.