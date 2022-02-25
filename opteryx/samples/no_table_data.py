"""
no table
---------

This is used to prepresent no table.
"""

if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(1, os.path.join(sys.path[0], "../.."))

import io
import base64
import pyarrow.parquet as pq  # type:ignore


class NoTable:
    @staticmethod
    def get():

        return pq.read_table(
            io.BytesIO(
                base64.b85decode(
                    b'P(e~L6$BLk6%tGp02Krh001bpFa00@0RR9M02K}uAS@LE6$BLq6$Tst001bpFa00~IRF3x00002001U@92Ei?H3R?#85jm*Z)|mKZWRm`0v1pfbS5??2q`QT1Qi4o0ss{N6$BLm0000L0vRkd02l^yV`yb<VHE-Z6#^v!7zSf+Y;|pJY`g#f02Trn92p!Yd>j=588rj|1{oLzV{dGAZEh6|76KMf7IY>yCI~4k6$BLo6#@Vi02Krk0ssI27El%fCI}XE6aWAj92g8iQc_P>I&))aWo=;?paCy0FE1}MK|w)5K~X_LK|w)5K}$hFcR@mDK}JDAXF)?}K|w)5K|(@7K}|tHK|w=7K}kVDK|w-6K}kVDK|w-6K|w)5ML|J9K~+IPK|w`9K~+IPXF)<|K}bPCcR@ixK~X_MK|w)5K|w)5MM6bEK|w)6cR@ixK}A79K|w)5K|w)5SwTTTLTX|%crjvEG(kZ@Q9(jMK}A79K|uf*A8=uEadl;MEn{$SEn#wUZ+9SeWpZ<AZ*CwrE-)@I85|q{002J$002-yQZW'
                )
            )
        )


if __name__ == "__main__":  # pragma: no cover

    md = NoTable().get()

    print(md.schema)
    print(md.shape)