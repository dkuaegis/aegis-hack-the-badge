Import("env")

from os.path import join

env.Replace(PROJECT_DATA_DIR=join(env.subst("$PROJECT_DIR"), "badapple_data"))
