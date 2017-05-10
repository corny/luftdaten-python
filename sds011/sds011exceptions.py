"""
Copyright 2016, Frank Heuer, Germany

This file is part of SDS011.

SDS011 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SDS011 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SDS011.  If not, see <http://www.gnu.org/licenses/>.

Diese Datei ist Teil von SDS011.

SDS011 ist Freie Software: Sie können es unter den Bedingungen
der GNU General Public License, wie von der Free Software Foundation,
Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren
veröffentlichten Version, weiterverbreiten und/oder modifizieren.

SDS011 wird in der Hoffnung, dass es nützlich sein wird, aber
OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
Siehe die GNU General Public License für weitere Details.

Sie sollten eine Kopie der GNU General Public License zusammen mit SDS011
erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.
"""

"""Moduel holding the exceptions for use in SDS011 class"""
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class WorkStateError(Error):
    """Exception raised for errors in the workingmode."""
    pass
class GetStatusError(Error):
    """Exception raised when initial getting the current sensor status won't work."""
    pass
class ReportModeError(Error):
    """Exception raised when sensor is in wrong reportmode for requested operation."""
    pass
class NoSensorResponse(Error):
    """Exception raised when sensor is unexpected not responding"""
    pass
