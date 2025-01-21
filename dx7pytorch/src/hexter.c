/* hexter DSSI software synthesizer plugin
 *
 * Copyright (C) 2004, 2009, 2011, 2012, 2014, 2018 Sean Bolton and others.
 *
 * Portions of this file may have come from Peter Hanappe's
 * Fluidsynth, copyright (C) 2003 Peter Hanappe and others.
 * Portions of this file may have come from Chris Cannam and Steve
 * Harris's public domain DSSI example code.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE.  See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the Free
 * Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301 USA.
 */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "hexter_types.h"
#include "hexter.h"
#include "hexter_synth.h"
#include "dx7_voice.h"
#include "dx7_voice_data.h"

/* ---- LADSPA interface ---- */

/*
 * hexter_activate
 *
 * implements LADSPA (*activate)()
 */
static void hexter_activate(hexter_instance_t* handle)
{
    hexter_instance_t *instance = (hexter_instance_t *)handle;

    hexter_instance_all_voices_off(instance);  /* stop all sounds immediately */
    instance->current_voices = 0;
    dx7_lfo_reset(instance);
}

/*
 * hexter_deactivate
 *
 * implements LADSPA (*deactivate)()
 */
void hexter_deactivate(hexter_instance_t* handle)
{
    hexter_instance_t *instance = (hexter_instance_t *)handle;

    hexter_instance_all_voices_off(instance);  /* stop all sounds immediately */
}

/*
 * hexter_cleanup
 *
 * implements LADSPA (*cleanup)()
 */
static void hexter_cleanup(hexter_instance_t* handle)
{
    hexter_instance_t *instance = (hexter_instance_t *)handle;
    int i;

    if (instance) {
        hexter_deactivate(instance);

        for (i = 0; i < HEXTER_MAX_POLYPHONY; i++) {
            if (instance->voice[i]) {
                free(instance->voice[i]);
                instance->voice[i] = NULL;
            }
        }
        free(instance);
    }
}


/*
 * hexter_instantiate
 *
 * implements LADSPA (*instantiate)()
 */
static hexter_instance_t*
hexter_instantiate(unsigned long sample_rate, dx7_patch_t * patch_buffer)
{
    hexter_instance_t *instance;
    int i;

    instance = (hexter_instance_t *)calloc(1, sizeof(hexter_instance_t));
    if (!instance) {
        return NULL;
    }

    /* do any per-instance one-time initialization here */
    for (i = 0; i < HEXTER_MAX_POLYPHONY; i++) {
        instance->voice[i] = dx7_voice_new();
        if (!instance->voice[i]) {
            DEBUG_MESSAGE(-1, " hexter_instantiate: out of memory!\n");
            hexter_cleanup(instance);
            return NULL;
        }
    }
    /*Assign patch buffer provided by Python.*/
    instance->patches = patch_buffer;

    instance->sample_rate = (float)sample_rate;
    instance->nugget_remains = 0;
    dx7_eg_init_constants(instance);  /* depends on sample rate */

    instance->note_id = 0;
    instance->polyphony = HEXTER_DEFAULT_POLYPHONY;
    instance->monophonic = DSSP_MONO_MODE_OFF;
    instance->max_voices = instance->polyphony;
    instance->current_voices = 0;
    instance->last_key = 0;
    //pthread_mutex_init(&instance->voicelist_mutex, NULL);
    //instance->voicelist_mutex_grab_failed = 0;
    //pthread_mutex_init(&instance->patches_mutex, NULL);
    instance->pending_program_change = -1;
    instance->current_program = 0;
    instance->overlay_program = -1;
    hexter_data_performance_init(instance->performance_buffer);
    hexter_data_patches_init(instance->patches);
    hexter_instance_select_program(instance, 0, 0);
    hexter_instance_init_controls(instance);

    return instance;
}


/** Modified version of hexter_run_synth on which we dont process any events.
    Events are generated externally. */
static void
hexter_run_synth(hexter_instance_t* handle, unsigned long sample_count, unsigned long samples_done)
{
    hexter_instance_t *instance = (hexter_instance_t *)handle;

    //unsigned long samples_done = 0;
    unsigned long burst_size;
    /* silence the buffer */
    memset(instance->output+samples_done, 0, sizeof(LADSPA_Data) * (sample_count-samples_done));
#if defined(DSSP_DEBUG) && (DSSP_DEBUG & DB_AUDIO)
*instance->output += 0.10f; /* add a 'buzz' to output so there's something audible even when quiescent */
#endif /* defined(DSSP_DEBUG) && (DSSP_DEBUG & DB_AUDIO) */


    while (samples_done < sample_count) {

        if (!instance->nugget_remains)
            instance->nugget_remains = HEXTER_NUGGET_SIZE;


        /* calculate the sample count (burst_size) for the next
         * hexter_instance_render_voices() call to be the smallest of:
         * - control calculation quantization size (HEXTER_NUGGET_SIZE,
         *     in samples)
         * - the number of samples remaining in an already-begun nugget
         *     (instance->nugget_remains)
         * - the number of samples left in this run
         */
        burst_size = HEXTER_NUGGET_SIZE;
        if (instance->nugget_remains < burst_size) {
            /* we're still in the middle of a nugget, so reduce the burst size
             * to end when the nugget ends */
            burst_size = instance->nugget_remains;
        }

        if (sample_count - samples_done < burst_size) {
            /* reduce burst size to end at end of this run */
            burst_size = sample_count - samples_done;
        }

        /* render the burst */
        hexter_instance_render_voices(instance, samples_done, burst_size,
                                      (burst_size == instance->nugget_remains));
        samples_done += burst_size;
        instance->nugget_remains -= burst_size;
    }
}

hexter_instance_t* hexter_init(unsigned long sample_rate,dx7_patch_t * patch_buffer)
    {
    //printf("[DEBUG] dxcore.so: Initializing tables . . .\n");
    dx7_voice_init_tables();
    
    //printf("[DEBUG] dxcore.so: Library called. Attemping to create hexter instance . . .\n");
    
    hexter_instance_t* instance = hexter_instantiate(16000,         //Sample rate.
                                                    patch_buffer);  //Patch buffer provided by Python.


    //printf("[DEBUG] dxcore.so: Adding tuning, volume and output controls\n"); //They are set by LADSPA in original hexter.
    //printf("[DEBUG] dxcore.so: Setting output buffer at %p\n",output_buffer);
    
    instance->tuning = malloc(1*sizeof(LADSPA_Data));
    instance->volume = malloc(1*sizeof(LADSPA_Data));
    *instance->tuning = 440.0f;
    *instance->volume = 1.0f;
    
    //printf("[DEBUG] dxcore.so: Activating instance %p . . .\n",instance);
    
    hexter_activate(instance);  //instance
    
    return instance;
    }

void reset_synth(hexter_instance_t* instance)
    {
    hexter_activate(instance);  //instance
    }

void synthesize(hexter_instance_t* instance,LADSPA_Data* output_buffer,unsigned long start_sample, unsigned long end_sample)
    {
    instance->output = output_buffer; //Managed by python.
    DEBUG_MESSAGE(-1,"Called run_synth with %p\n",output_buffer);
    //printf("[DEBUG] dxcore.so: Rendering audio . . .\n");
    hexter_run_synth(instance, //instance
                     end_sample,    //Last sample number
                     start_sample);       //Samples done

    return;
    }

void hexter_clean_and_exit(hexter_instance_t* instance)
    {
    free(instance->tuning);
    free(instance->volume);    
    hexter_cleanup(instance);
    
    return;
    }
