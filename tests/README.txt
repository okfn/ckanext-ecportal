Important notice for Vim users regarding special characters
===========================================================

Can you see these greek characters correctly rendered? πυρηνικά

If not, please make sure that the Vim version you are using is compiled
with `multi_byte` support. You can check it running `vim --version` on the
command line or the `:version` command from the editor and seeing if this
option is displayed: `+multi_byte` (note the plus sign).

If you are on Ubuntu and don't want to recompile Vim you can install the
package `vim-nox`, which is compiled with this option.

If your version of vim does not support `multi_byte` it may save incorrectly
the special characters and cause errors to fail (This is probably only
important for search related tests). Please use another version of vim (see
above) or another editor to edit the file in question (gedit works fine).
