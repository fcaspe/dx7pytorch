CFLAGS = -fPIC -Wall -DUSE_HEXTER_FLOATING_POINT -DHEXTER_USE_FLOATING_POINT -O2 #-DLIB_DEBUG

PATH_INCLUDES = ./dx7pytorch/src/
SOURCE_DIR = ./dx7pytorch/src

OBJS_TB = dx7_voice.o dx7_voice_patches.o dx7_voice_tables.o hexter_synth.o dx7_voice_data.o dx7_voice_render.o hexter.o

LIB_NAME = dxcore.so
BIN_TB = test
LIBS = -lm

all: link_all
	rm -f $(OBJS_TB)

link_all: $(OBJS_TB)
	gcc -shared -Wl,-soname,$(LIB_NAME) -o $(LIB_NAME) $(OBJS_TB) $(LIBS) #-L$(PATH_LIB)
	#gcc -o $(BIN_TB) $(OBJS_TB) $(LIBS)

#main.o: $(SOURCE_DIR)/main.c
#	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/main.c

dx7_voice.o: $(SOURCE_DIR)/dx7_voice.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/dx7_voice.c

hexter.o: $(SOURCE_DIR)/hexter.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/hexter.c

hexter_synth.o: $(SOURCE_DIR)/hexter_synth.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/hexter_synth.c

dx7_voice_render.o: $(SOURCE_DIR)/dx7_voice_render.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/dx7_voice_render.c

dx7_voice_data.o: $(SOURCE_DIR)/dx7_voice_data.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/dx7_voice_data.c

dx7_voice_tables.o: $(SOURCE_DIR)/dx7_voice_tables.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/dx7_voice_tables.c

dx7_voice_patches.o: $(SOURCE_DIR)/dx7_voice_patches.c
	gcc $(CFLAGS) -I$(PATH_INCLUDES) -c $(SOURCE_DIR)/dx7_voice_patches.c


clean:
	rm -f $(BIN_TB) $(OBJS_TB)

