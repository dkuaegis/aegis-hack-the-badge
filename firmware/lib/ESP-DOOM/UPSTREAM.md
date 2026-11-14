This is the `src/` directory and GPL-2.0 license from
[rear16/ESP-DOOM](https://github.com/rear16/ESP-DOOM), commit
`92bd5c3968197683041e7917e5f9e709164ba1fd`. The Aegis display and
three-button adapter lives in `firmware/src/doom_badge.cpp`. `src/i_sound.c`
selects the badge's monophonic buzzer music module when `AEGIS_DOOM` is set.
`src/DoomGlue.cpp` skips the upstream RGB565 conversion for that build because
the badge display reads the indexed frame buffer directly.
