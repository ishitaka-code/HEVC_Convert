# -*- coding: utf-8 -*-

import datetime
import json
import os.path
import shutil
import subprocess
import sys
import tkinter.filedialog


tk = tkinter.Tk()
tk.withdraw()
# このファイルパス・フォルダパスの取得
path_thisScript = os.path.abspath(__file__)
dirpath_this = os.path.dirname(__file__)
# プログラムのパス
path_x265 = os.path.abspath(dirpath_this + r"\bin\x265_3.5+73_x64\x265_3.5+73_x64.exe")
path_ffprobe = os.path.abspath(dirpath_this + r"\bin\ffmpeg-master-latest-win64-gpl-shared\bin\ffprobe.exe")
path_ffmpeg = os.path.abspath(dirpath_this + r"\bin\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe")
path_mkvmerge = os.path.abspath(dirpath_this + r"\bin\mkvtoolnix-64-bit-72.0.0\mkvtoolnix\mkvmerge.exe")
# ドラッグアンドドロップによる引数でファイル名を取得する．
args = sys.argv
del args[0]
filenames = tuple(args)
# askopenfilenames ダイヤログで複数ファイルを選択する。
if len(filenames) < 1:
    filenames = tkinter.filedialog.askopenfilenames()
if len(filenames) < 1:
    sys.exit()
# CRF値を入力
while True:
    try:
        print("x265.exeのCRF値を入力して下さい．指定可能範囲：0～51")
        print("ソフトを終了するときは-1を入力して下さい．")
        hevc_crf = int(input("CRF="))
        if 0 <= hevc_crf <= 51:
            break
        elif hevc_crf == -1:
            sys.exit()
    except ValueError:
        pass

StartTime = datetime.datetime.now()
for inputfile in filenames:
    print(os.path.basename(inputfile) + "を処理中．．．．．．")
    # x265で変換
    print("x265.exe開始：" + str(datetime.datetime.now()))
    temp_hevcfile = inputfile + "_temp.hevc"
    cmd_string = "\"{path_ffmpeg}\" -loglevel warning -i \"{inputfile}\" -an -sn -f yuv4mpegpipe - | " \
                 "\"{path_x265}\" --log-level warning --input - --y4m --profile main10 --output-depth 10 " \
                 "--crf {hevc_crf} --output \"{temp_hevcfile}\"".format(**locals())
    subprocess.run(cmd_string, shell=True)

    # ffprobeでJSON形式データ取得
    ffprobe_cmd = "\"{path_ffprobe}\" -i \"{inputfile}\" -loglevel quiet -show_streams -print_format " \
                  "json".format(**locals())
    cmd_stdout, cmd_stderr = subprocess.Popen(ffprobe_cmd, shell=True, stdout=subprocess.PIPE).communicate()
    ffprobe_jsondata = json.loads(cmd_stdout)

    # wmaを見つけたらaacに変換
    wma_index_list = []
    temp_aacfile_list = []
    for i in range(len(ffprobe_jsondata["streams"])):
        if ffprobe_jsondata["streams"][i]["codec_name"].find("wma") != -1:
            wma_index = ffprobe_jsondata["streams"][i]["index"]
            print("index:{wma_index}にwmaを見つけました。".format(**locals()))
            wma_index_list.append(wma_index)
            temp_aacfile_list.append(inputfile + "_index" + str(wma_index) + "_temp.aac")
    for i in range(len(wma_index_list)):
        wma_index = wma_index_list[i]
        temp_aacfile = temp_aacfile_list[i]
        print("index:{wma_index}をaacに変換開始：".format(**locals()) + str(datetime.datetime.now()))
        cmd_string = "\"{path_ffmpeg}\" -loglevel warning -i \"{inputfile}\" -vn -sn -c:a aac -b:a 128k " \
                     "-map 0:{wma_index} \"{temp_aacfile}\"".format(**locals())
        subprocess.run(cmd_string, shell=True)

    # dtsを見つけたらflacに変換
    dts_index_list = []
    temp_flacfile_list = []
    for i in range(len(ffprobe_jsondata["streams"])):
        if ffprobe_jsondata["streams"][i]["codec_name"] == "dts":
            if ffprobe_jsondata["streams"][i]["tags"]["language"] == "eng" \
                    or ffprobe_jsondata["streams"][i]["tags"]["language"] == "jpn":
                dts_index = ffprobe_jsondata["streams"][i]["index"]
                print("index:{dts_index}にengかjpnのdtsを見つけました。".format(**locals()))
                dts_index_list.append(dts_index)
                temp_flacfile_list.append(inputfile + "_index" + str(dts_index) + "_temp.flac")
    for i in range(len(dts_index_list)):
        dts_index = dts_index_list[i]
        temp_flacfile = temp_flacfile_list[i]
        print("index:{dts_index}をflacに変換開始：".format(**locals()) + str(datetime.datetime.now()))
        cmd_string = "\"{path_ffmpeg}\" -loglevel warning -i \"{inputfile}\" -vn -sn -c:a flac " \
                     "-map 0:{dts_index} \"{temp_flacfile}\"".format(**locals())
        subprocess.run(cmd_string, shell=True)

    # mkvを作成
    print("mkvmerge.exe開始：" + str(datetime.datetime.now()))
    if len(wma_index_list + dts_index_list) == 0:
        AudioOptionStr = " --no-video \"{inputfile}\"".format(**locals())
    elif len(wma_index_list) != 0:  # aac（wmaから変換）があればmkvに追加
        AudioOptionStr = ""
        for i in range(len(wma_index_list)):
            AudioOptionStr += " \"{}\"".format(temp_aacfile_list[i])
    elif len(dts_index_list) != 0:  # flac（dtsから変換）があればmkvに追加
        AudioOptionStr = " --no-video \"{inputfile}\"".format(**locals())
        for i in range(len(dts_index_list)):
            AudioOptionStr += " \"{}\"".format(temp_flacfile_list[i])
    else:
        AudioOptionStr = ""
    f_splitpath, f_splitext = os.path.splitext(inputfile)
    outputfile = f_splitpath + " [HEVC10bit_crf" + str(hevc_crf) + "].mkv"
    cmd_string = "\"{path_mkvmerge}\" -q --output \"{outputfile}\" --no-audio \"{temp_hevcfile}\"".format(
        **locals()) + AudioOptionStr
    subprocess.run(cmd_string, shell=True)

    # 後処理
    print("tempファイル削除：" + str(datetime.datetime.now()))
    os.remove(temp_hevcfile)
    if len(wma_index_list) != 0:
        for i in range(len(wma_index_list)):
            os.remove(temp_aacfile_list[i])
    if len(dts_index_list) != 0:
        for i in range(len(dts_index_list)):
            os.remove(temp_flacfile_list[i])
    # CompFileDir = os.path.dirname(inputfile) + "\エンコード元ファイル"
    # if not os.path.exists(CompFileDir):
    #     os.mkdir(CompFileDir)
    # shutil.move(inputfile, CompFileDir)

FinishTime = datetime.datetime.now()
print("-" * 50)
print("開始時刻：" + str(StartTime))
print("終了時刻：" + str(FinishTime))
print("全ファイル合計処理時間：" + str(FinishTime - StartTime))
print("-" * 50)

input("\n終了するには何かキーを入力してください．．．")
