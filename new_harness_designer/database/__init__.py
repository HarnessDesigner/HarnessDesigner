"""
The database system is several layers which consists of a "config" database,
"global" database and "project" database.

config_db
---------

The config database store data that is persistant between restarts of the UI.
It hold settings like window size and positioning, the last project that has
been loaded. etc. this database stored it's data using sqlite and it is saved
to the local file system. This is done because the things that it stores would
be unique to where the program is being ran. I may in the future move this to
allow the data to be loaded from a network database and the data would be
specific to a logged in user.

to Use the config database you need to import the config module. It internally
handles how the data is to be saved in the database. It creates the necessary
tables and colums on the fly.

Example Use:

    # imports are relitive to the location of this file

    from .. import config as _config


    class Config(metaclass=_config.Config):
        position = (0, 0)
        size = (1024, 768)


    print(Config.position)
    Config.position = (300, 500)
    print(Config.position)


More advanced use


    class AdvancedConfig(metaclass=_config.Config):
        class NestedConfigClass:
            position = (0, 0)
            size = (1024, 768)

    print(AdvancedConfig.NestedConfigClass.position)
    AdvancedConfig.NestedConfigClass.position = (300, 500)
    print(AdvancedConfig.NestedConfigClass.position)


If you do not want something in the Config class to actually be stored then
prefix the attribute anme with an `_`.

That is all there is to it, Very painless and easy to use. When the program starts
it will automatically populte the classes with the stpored data and on program exit
it will save the data in those classes.



"""