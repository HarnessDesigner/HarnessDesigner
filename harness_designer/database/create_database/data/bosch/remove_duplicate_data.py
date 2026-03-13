import os


data_path = 'data'


# duplicate_data = {}
#
# files = [os.path.join(data_path, file) for file in os.listdir(data_path)]
#
# for file1 in files:
#     with open(file1, 'rb') as f:
#         data1 = f.read()
#
#     duplicate_data[file1] = []
#
#     for file2 in files[:]:
#         if file1 == file2:
#             continue
#
#         if file2 in duplicate_data:
#             continue
#
#         with open(file2, 'rb') as f:
#             data2 = f.read()
#
#         if data2 == data1:
#             duplicate_data[file1].append(file2)
#             files.remove(file2)
#

duplicate_files = {
    'data\\1 280 703 031.pdf': 'data\\1 280 703 026.pdf',
    'data\\1 284 485 112.pdf': 'data\\1 284 485 110.pdf',
    'data\\1 284 485 114.pdf': 'data\\1 284 485 110.pdf',
    'data\\1 284 485 120.pdf': 'data\\1 284 485 110.pdf',
    'data\\1 928 300 528.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 300 529.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 300 530.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 300 531.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 300 694.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 422.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 423.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 424.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 428.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 429.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 403 430.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 404 886.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 404 887.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 404 888.pdf': 'data\\1 928 300 527.pdf',
    'data\\1 928 300 600.pdf': 'data\\1 928 300 599.pdf',
    'data\\1 928 300 601.pdf': 'data\\1 928 300 599.pdf',
    'data\\1 928 300 935.pdf': 'data\\1 928 300 934.pdf',
    'data\\1 928 300 936.pdf': 'data\\1 928 300 934.pdf',
    'data\\1 928 301 084.pdf': 'data\\1 928 301 083.pdf',
    'data\\1 928 301 087.pdf': 'data\\1 928 301 083.pdf',
    'data\\1 928 301 118.pdf': 'data\\1 928 301 083.pdf',
    'data\\1 928 401 984.pdf': 'data\\1 928 401 980.pdf',
    'data\\1 928 401 985.pdf': 'data\\1 928 401 980.pdf',
    'data\\1 928 401 986.pdf': 'data\\1 928 401 980.pdf',
    'data\\1 928 401 987.pdf': 'data\\1 928 401 980.pdf',
    'data\\1 928 402 412.pdf': 'data\\1 928 402 404.pdf',
    'data\\1 928 403 490.pdf': 'data\\1 928 402 404.pdf',
    'data\\1 928 402 449.pdf': 'data\\1 928 402 448.pdf',
    'data\\1 928 402 452.pdf': 'data\\1 928 402 448.pdf',
    'data\\1 928 402 806.pdf': 'data\\1 928 402 448.pdf',
    'data\\1 928 402 906.pdf': 'data\\1 928 402 448.pdf',
    'data\\1 928 402 579.pdf': 'data\\1 928 402 571.pdf',
    'data\\1 928 402 587.pdf': 'data\\1 928 402 571.pdf',
    'data\\1 928 402 595.pdf': 'data\\1 928 402 571.pdf',
    'data\\1 928 402 603.pdf': 'data\\1 928 402 571.pdf',
    'data\\1 928 404 420.pdf': 'data\\1 928 402 908.pdf',
    'data\\1 928 403 112.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 126.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 137.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 192.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 196.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 198.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 200.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 202.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 204.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 222.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 698.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 722.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 870.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 403 920.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 404 221.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 404 627.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 404 629.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 404 707.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 405 184.pdf': 'data\\1 928 403 110.pdf',
    'data\\1 928 404 691.stp': 'data\\1 928 403 112.stp',
    'data\\1 928 403 137.stp': 'data\\1 928 403 126.stp',
    'data\\1 928 403 722.stp': 'data\\1 928 403 126.stp',
    'data\\1 928 404 635.stp': 'data\\1 928 403 453.stp',
    'data\\1 928 404 777.pdf': 'data\\1 928 403 462.pdf',
    'data\\1 928 403 736.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 738.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 740.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 742.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 836.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 874.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 876.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 966.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 968.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 403 970.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 072.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 073.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 074.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 075.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 114.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 213.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 525.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 655.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 656.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 657.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 658.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 678.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 745.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 825.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 993.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 405 086.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 405 148.pdf': 'data\\1 928 403 732.pdf',
    'data\\1 928 404 658.stp': 'data\\1 928 403 736.stp',
    'data\\1 928 404 993.stp': 'data\\1 928 403 736.stp',
    'data\\1 928 403 836.stp': 'data\\1 928 403 738.stp',
    'data\\1 928 404 525.stp': 'data\\1 928 403 740.stp',
    'data\\1 928 404 691.pdf': 'data\\1 928 403 913.pdf',
    'data\\1 928 404 627.stp': 'data\\1 928 403 913.stp',
    'data\\1 928 405 184.stp': 'data\\1 928 403 913.stp',
    'data\\1 928 404 707.stp': 'data\\1 928 403 920.stp',
    'data\\1 928 403 968.stp': 'data\\1 928 403 966.stp',
    'data\\1 928 403 970.stp': 'data\\1 928 403 966.stp',
    'data\\1 928 404 656.stp': 'data\\1 928 403 966.stp',
    'data\\1 928 404 657.stp': 'data\\1 928 403 966.stp',
    'data\\1 928 404 074.stp': 'data\\1 928 404 073.stp',
    'data\\1 928 405 148.stp': 'data\\1 928 404 073.stp',
    'data\\1 928 404 197.pdf': 'data\\1 928 404 196.pdf',
    'data\\1 928 404 200.pdf': 'data\\1 928 404 199.pdf',
    'data\\1 928 404 202.pdf': 'data\\1 928 404 201.pdf',
    'data\\1 928 404 227.pdf': 'data\\1 928 404 226.pdf',
    'data\\1 928 404 706.pdf': 'data\\1 928 404 226.pdf',
    'data\\1 928 405 136.pdf': 'data\\1 928 404 226.pdf',
    'data\\1 928 404 706.stp': 'data\\1 928 404 226.stp',
    'data\\1 928 404 276.pdf': 'data\\1 928 404 275.pdf',
    'data\\1 928 404 276.stp': 'data\\1 928 404 275.stp',
    'data\\1 928 404 543.pdf': 'data\\1 928 404 375.pdf',
    'data\\1 928 404 408.pdf': 'data\\1 928 404 406.pdf',
    'data\\1 928 404 491.pdf': 'data\\1 928 404 406.pdf',
    'data\\1 928 404 494.pdf': 'data\\1 928 404 410.pdf',
    'data\\1 928 404 797.pdf': 'data\\1 928 404 410.pdf',
    'data\\1 928 404 623.pdf': 'data\\1 928 404 563.pdf',
    'data\\1 928 404 621.pdf': 'data\\1 928 404 566.pdf',
    'data\\1 928 404 880.pdf': 'data\\1 928 404 566.pdf',
    'data\\1 928 405 642.pdf': 'data\\1 928 404 648.pdf',
    'data\\1 928 405 643.pdf': 'data\\1 928 404 648.pdf',
    'data\\1 928 405 642.stp': 'data\\1 928 404 648.stp',
    'data\\1 928 404 670.pdf': 'data\\1 928 404 669.pdf',
    'data\\1 928 404 900.pdf': 'data\\1 928 404 669.pdf',
    'data\\1 928 404 902.pdf': 'data\\1 928 404 669.pdf',
    'data\\1 928 405 109.pdf': 'data\\1 928 404 669.pdf',
    'data\\1 928 404 761.pdf': 'data\\1 928 404 760.pdf',
    'data\\1 928 404 918.pdf': 'data\\1 928 404 773.pdf',
    'data\\1 928 404 916.pdf': 'data\\1 928 404 780.pdf',
    'data\\1 928 404 927.pdf': 'data\\1 928 404 781.pdf',
    'data\\1 928 404 902.stp': 'data\\1 928 404 900.stp',
    'data\\1 928 404 982.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 153.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 154.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 155.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 167.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 168.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 169.pdf': 'data\\1 928 404 981.pdf',
    'data\\1 928 405 559.pdf': 'data\\1 928 405 064.pdf',
    'data\\1 928 405 071.pdf': 'data\\1 928 405 069.pdf',
    'data\\1 928 405 072.pdf': 'data\\1 928 405 070.pdf',
    'data\\1 928 405 074.pdf': 'data\\1 928 405 073.pdf',
    'data\\1 928 405 077.pdf': 'data\\1 928 405 076.pdf',
    'data\\1 928 405 085.pdf': 'data\\1 928 405 084.pdf',
    'data\\1 928 405 138.pdf': 'data\\1 928 405 091.pdf',
    'data\\1 928 405 159.pdf': 'data\\1 928 405 091.pdf',
    'data\\1 928 405 111.pdf': 'data\\1 928 405 110.pdf',
    'data\\1 928 405 141.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 372.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 373.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 374.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 375.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 387.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 414.pdf': 'data\\1 928 405 140.pdf',
    'data\\1 928 405 161.pdf': 'data\\1 928 405 160.pdf',
    'data\\1 928 405 216.pdf': 'data\\1 928 405 160.pdf',
    'data\\1 928 405 217.pdf': 'data\\1 928 405 160.pdf',
    'data\\1 928 405 164.pdf': 'data\\1 928 405 162.pdf',
    'data\\1 928 405 165.pdf': 'data\\1 928 405 163.pdf',
    'data\\1 928 405 240.pdf': 'data\\1 928 405 239.pdf',
    'data\\1 928 405 248.pdf': 'data\\1 928 405 247.pdf',
    'data\\1 928 405 383.pdf': 'data\\1 928 405 311.pdf',
    'data\\1 928 405 313.pdf': 'data\\1 928 405 312.pdf',
    'data\\1 928 405 314.pdf': 'data\\1 928 405 312.pdf',
    'data\\1 928 405 384.pdf': 'data\\1 928 405 312.pdf',
    'data\\1 928 405 316.pdf': 'data\\1 928 405 315.pdf',
    'data\\1 928 405 320.pdf': 'data\\1 928 405 319.pdf',
    'data\\1 928 405 328.pdf': 'data\\1 928 405 327.pdf',
    'data\\1 928 405 699.pdf': 'data\\1 928 405 327.pdf',
    'data\\1 928 405 613.pdf': 'data\\1 928 405 453.pdf',
    'data\\1 928 405 614.pdf': 'data\\1 928 405 453.pdf',
    'data\\1 928 405 615.pdf': 'data\\1 928 405 453.pdf',
    'data\\1 928 405 610.pdf': 'data\\1 928 405 456.pdf',
    'data\\1 928 405 611.pdf': 'data\\1 928 405 456.pdf',
    'data\\1 928 405 612.pdf': 'data\\1 928 405 456.pdf',
    'data\\1 928 405 524.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 525.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 526.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 527.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 528.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 529.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 530.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 531.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 532.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 587.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 588.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 630.pdf': 'data\\1 928 405 521.pdf',
    'data\\1 928 405 522.stp': 'data\\1 928 405 521.stp',
    'data\\1 928 405 529.stp': 'data\\1 928 405 521.stp',
    'data\\1 928 405 530.stp': 'data\\1 928 405 521.stp',
    'data\\1 928 405 532.stp': 'data\\1 928 405 521.stp',
    'data\\1 928 405 523.pdf': 'data\\1 928 405 522.pdf',
    'data\\1 928 405 524.stp': 'data\\1 928 405 523.stp',
    'data\\1 928 405 528.stp': 'data\\1 928 405 523.stp',
    'data\\1 928 405 531.stp': 'data\\1 928 405 523.stp',
    'data\\1 928 405 526.stp': 'data\\1 928 405 525.stp',
    'data\\1 928 405 587.stp': 'data\\1 928 405 525.stp',
    'data\\1 928 405 588.stp': 'data\\1 928 405 525.stp',
    'data\\1 928 405 763.pdf': 'data\\1 928 405 762.pdf',
    'data\\1 928 405 765.pdf': 'data\\1 928 405 762.pdf',
    'data\\1 928 405 783.pdf': 'data\\1 928 405 782.pdf',
    'data\\1 928 405 784.pdf': 'data\\1 928 405 782.pdf',
    'data\\1 928 406 074.pdf': 'data\\1 928 406 072.pdf',
    'data\\1 928 406 092.pdf': 'data\\1 928 406 091.pdf',
    'data\\1 928 406 093.pdf': 'data\\1 928 406 091.pdf',
    'data\\1 928 406 094.pdf': 'data\\1 928 406 091.pdf',
    'data\\1 928 406 097.pdf': 'data\\1 928 406 096.pdf',
    'data\\1 928 406 098.pdf': 'data\\1 928 406 096.pdf',
    'data\\1 928 406 099.pdf': 'data\\1 928 406 096.pdf',
    'data\\1 928 406 104.pdf': 'data\\1 928 406 102.pdf',
    'data\\1 928 406 376.pdf': 'data\\1 928 406 322.pdf',
    'data\\1 928 492 556.pdf': 'data\\1 928 492 555.pdf',
    'data\\1 928 498 748.pdf': 'data\\1 928 492 555.pdf',
    'data\\1 928 499 044.pdf': 'data\\1 928 492 555.pdf',
    'data\\1 928 499 045.pdf': 'data\\1 928 492 555.pdf',
    'data\\1 928 498 001.pdf': 'data\\1 928 498 000.pdf',
    'data\\1 928 498 002.pdf': 'data\\1 928 498 000.pdf',
    'data\\1 928 498 003.pdf': 'data\\1 928 498 000.pdf',
    'data\\1 928 498 014.pdf': 'data\\1 928 498 013.pdf',
    'data\\1 928 498 015.pdf': 'data\\1 928 498 013.pdf',
    'data\\1 928 498 016.pdf': 'data\\1 928 498 013.pdf',
    'data\\1 928 498 055.pdf': 'data\\1 928 498 054.pdf',
    'data\\1 928 498 056.pdf': 'data\\1 928 498 054.pdf',
    'data\\1 928 498 057.pdf': 'data\\1 928 498 054.pdf',
    'data\\1 928 498 058.pdf': 'data\\1 928 498 054.pdf',
    'data\\1 928 498 059.pdf': 'data\\1 928 498 054.pdf',
    'data\\1 928 498 103.pdf': 'data\\1 928 498 102.pdf',
    'data\\1 928 498 105.pdf': 'data\\1 928 498 104.pdf',
    'data\\1 928 498 107.pdf': 'data\\1 928 498 106.pdf',
    'data\\1 928 498 141.pdf': 'data\\1 928 498 140.pdf',
    'data\\1 928 498 143.pdf': 'data\\1 928 498 140.pdf',
    'data\\1 928 498 144.pdf': 'data\\1 928 498 140.pdf',
    'data\\1 928 498 146.pdf': 'data\\1 928 498 140.pdf',
    'data\\1 928 498 147.pdf': 'data\\1 928 498 140.pdf',
    'data\\1 928 498 164.pdf': 'data\\1 928 498 163.pdf',
    'data\\1 928 498 204.pdf': 'data\\1 928 498 203.pdf',
    'data\\1 928 498 209.pdf': 'data\\1 928 498 203.pdf',
    'data\\1 928 498 210.pdf': 'data\\1 928 498 203.pdf',
    'data\\1 928 498 211.pdf': 'data\\1 928 498 203.pdf',
    'data\\1 928 498 213.pdf': 'data\\1 928 498 212.pdf',
    'data\\1 928 498 214.pdf': 'data\\1 928 498 212.pdf',
    'data\\1 928 498 690.pdf': 'data\\1 928 498 650.pdf',
    'data\\1 928 498 674.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 675.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 676.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 677.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 678.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 681.pdf': 'data\\1 928 498 673.pdf',
    'data\\1 928 498 805.pdf': 'data\\1 928 498 705.pdf',
    'data\\1 928 498 741.pdf': 'data\\1 928 498 706.pdf',
    'data\\1 928 498 742.pdf': 'data\\1 928 498 707.pdf',
    'data\\1 928 498 744.pdf': 'data\\1 928 498 709.pdf',
    'data\\1 928 498 721.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 722.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 723.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 725.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 726.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 727.pdf': 'data\\1 928 498 720.pdf',
    'data\\1 928 498 750.pdf': 'data\\1 928 498 749.pdf',
    'data\\1 928 498 751.pdf': 'data\\1 928 498 749.pdf',
    'data\\1 928 498 752.pdf': 'data\\1 928 498 749.pdf',
    'data\\1 928 499 399.pdf': 'data\\1 928 498 807.pdf',
    'data\\1 928 499 629.pdf': 'data\\1 928 498 807.pdf',
    'data\\1 928 499 630.pdf': 'data\\1 928 498 807.pdf',
    'data\\1 928 498 809.pdf': 'data\\1 928 498 808.pdf',
    'data\\1 928 498 810.pdf': 'data\\1 928 498 808.pdf',
    'data\\1 928 498 811.pdf': 'data\\1 928 498 808.pdf',
    'data\\1 928 498 992.pdf': 'data\\1 928 498 991.pdf',
    'data\\1 928 498 993.pdf': 'data\\1 928 498 991.pdf',
    'data\\1 928 499 357.pdf': 'data\\1 928 498 991.pdf',
    'data\\1 928 499 358.pdf': 'data\\1 928 498 991.pdf',
    'data\\1 928 499 359.pdf': 'data\\1 928 498 991.pdf',
    'data\\1 928 499 115.pdf': 'data\\1 928 499 114.pdf',
    'data\\1 928 499 260.pdf': 'data\\1 928 499 259.pdf',
    'data\\1 928 499 261.pdf': 'data\\1 928 499 259.pdf',
    'data\\1 928 499 262.pdf': 'data\\1 928 499 259.pdf',
}


# print('{')
# for key in sorted(list(duplicate_data.keys())):
#     values = duplicate_data[key]
#
#     if values:
#         for p in sorted(values):
#             print(f"    '{p}': '{key}',")
#             duplicate_files[p] = key
#
# print('}')


import json

with open('boots.json', 'r') as f:
    boots = json.loads(f.read())

with open('covers.json', 'r') as f:
    covers = json.loads(f.read())

with open('cpa_locks.json', 'r') as f:
    cpa_locks = json.loads(f.read())

with open('housings.json', 'r') as f:
    housings = json.loads(f.read())

with open('seals.json', 'r') as f:
    seals = json.loads(f.read())

with open('terminals.json', 'r') as f:
    terminals = json.loads(f.read())

with open('tpa_locks.json', 'r') as f:
    tpa_locks = json.loads(f.read())


def swap_files(container, r_file, t_file):
    removal_part_number = os.path.splitext(os.path.split(r_file)[-1])[0]
    target_part_number = os.path.splitext(os.path.split(t_file)[-1])[0]

    for p in container:
        if p['cad'] is not None and p['cad'] == r_file:
            p['shared_cad'] = target_part_number
            p['cad'] = t_file
            print('CAD:', removal_part_number, '--->', target_part_number)
            return True

        elif p['model3d'] is not None and p['model3d'] == r_file:
            p['shared_model3d'] = target_part_number
            p['model3d'] = t_file
            print('MODEL3D:', removal_part_number, '--->', target_part_number)
            return True

    return False


for removal_file, target_file in duplicate_files.items():

    if swap_files(boots, removal_file, target_file):
        continue

    if swap_files(covers, removal_file, target_file):
        continue

    if swap_files(cpa_locks, removal_file, target_file):
        continue

    if swap_files(housings, removal_file, target_file):
        continue

    if swap_files(seals, removal_file, target_file):
        continue

    if swap_files(terminals, removal_file, target_file):
        continue

    if swap_files(tpa_locks, removal_file, target_file):
        continue

    print(removal_file, target_file)
    # raise RuntimeError('This should not happen')


def change_paths(container):
    for part in container:
        if part['model3d'] is not None:
            part['model3d'] = part['model3d'].replace('\\', '/')

        if part['cad'] is not None:
            part['cad'] = part['cad'].replace('\\', '/')


change_paths(boots)

with open('new_boots.json', 'w') as f:
    f.write(json.dumps(boots, indent=4))

change_paths(covers)

with open('new_covers.json', 'w') as f:
    f.write(json.dumps(covers, indent=4))

change_paths(cpa_locks)

with open('new_cpa_locks.json', 'w') as f:
    f.write(json.dumps(cpa_locks, indent=4))

change_paths(housings)

with open('new_housings.json', 'w') as f:
    f.write(json.dumps(housings, indent=4))

change_paths(seals)

with open('new_seals.json', 'w') as f:
    f.write(json.dumps(seals, indent=4))

change_paths(terminals)

with open('new_terminals.json', 'w') as f:
    f.write(json.dumps(terminals, indent=4))

change_paths(tpa_locks)

with open('new_tpa_locks.json', 'w') as f:
    f.write(json.dumps(tpa_locks, indent=4))
