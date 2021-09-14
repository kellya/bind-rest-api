#!/usr/bin/env python
import re
import sys
from bind_rest_api import cli

if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    sys.exit(cli.main())
