## FilterData properties

### Graphics: Common

See: 
* https://github.com/LibreOffice/core/blob/5bd1ac0083bf6047fd1b977f24ae5ffb7018f2a8/vcl/source/filter/graphicfilter.cxx#L789
* https://github.com/LibreOffice/core/blob/16ee4d434692387419e6493aefba4312b2d80a8c/filter/source/graphic/GraphicExportFilter.cxx#L41

* PixelWidth (Integer)
* PixelHeight (Integer)
* LogicalWidth (Integer, 1/100 of mm)
* LogicalHeight (Integer, 1/100 of mm)
* ExportMode (Integer)
  * 0: default, no scaling
  * 1: Resolution is set
  * 2: Size is set (default when LogicalWidth or LogicalHeight is set)
  
### Graphics: JPEG


* Quality (Integer, range 1-100, default 75)
* ColorMode (Integer, default 0)
  * 0: RGB
  * 1: Grayscale

### Graphics: PNG


* Compression (Integer, default 6, range 0-9)
* Interlaced (Integer, default 1)

### Printer properties

* Name (String): Name of the printer
* PaperFormat (Enum, com.sun.star.view.PaperFormat.*)
* PaperOrientation (Enum, com.sun.star.view.PaperOrientation.{PORTRAIT,LANDSCAPE})
* PaperSize (com.sun.star.awt.Size): Size in 1/100 mm
* CopyCount (Integer): Number of copies
* FileName (String): File name if printing to a file
* Collate (Boolean): Collate pages
* Sort (Boolean): Sort pages of multiple copies
* Pages (String, "1-3; 7; 9"): Pages to print
