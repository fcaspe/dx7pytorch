# Compiler and Flags
CFLAGS = -fPIC -Wall -DUSE_HEXTER_FLOATING_POINT -DHEXTER_USE_FLOATING_POINT -O2 #-DLIB_DEBUG
LDFLAGS =
LIBS = -lm

# Paths
PATH_INCLUDES = ./dx7pytorch/src/
SOURCE_DIR = ./dx7pytorch/src/

# Source Files
OBJS_TB = dx7_voice.o dx7_voice_patches.o dx7_voice_tables.o hexter_synth.o dx7_voice_data.o dx7_voice_render.o hexter.o

# Detect Platform
UNAME := $(shell uname -s | tr '[:upper:]' '[:lower:]')
ifeq ($(UNAME), darwin)  # macOS
    LIB_NAME = dxcore.dylib
    SHARED_FLAGS = -dynamiclib -Wl,-install_name,@rpath/$(LIB_NAME)
else ifeq ($(OS), Windows_NT)  # Windows
    LIB_NAME = dxcore.dll
    SHARED_FLAGS = -shared
else  # Default to Linux
    LIB_NAME = dxcore.so
    SHARED_FLAGS = -shared -Wl,-soname,$(LIB_NAME)
endif

# Targets
all: link_all
	rm -f $(OBJS_TB)

link_all: $(OBJS_TB)
	gcc $(CFLAGS) $(SHARED_FLAGS) -o $(LIB_NAME) $(OBJS_TB) $(LIBS)

# Object File Compilation Rules
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

# Clean Target
clean:
	rm -f $(LIB_NAME) $(OBJS_TB)
