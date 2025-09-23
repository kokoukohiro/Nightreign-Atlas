import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os

# 文字をいったん描画してから横方向だけ縮めて貼り付ける
def draw_narrow_text(base_img, xy, text, font, fill, scale_x=0.80, **kwargs):
    """
    文字を一度描いて横方向だけ縮めて貼り付ける。
    縮小前後で“見た目の中心”が変わらないように、貼り付け時にx座標を自動補正する。
    """
    d = ImageDraw.Draw(base_img)
    bbox = d.textbbox((0, 0), text, font=font, **kwargs)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(tmp)
    d2.text((-bbox[0], -bbox[1]), text, font=font, fill=fill, **kwargs)

    new_w = max(1, int(w * scale_x))
    squeezed = tmp.resize((new_w, h), resample=Image.Resampling.BICUBIC)

    x, y = xy
    x = x + (w - new_w) // 2  # 中央を維持するための補正
    base_img.paste(squeezed, (x, y), squeezed)

def generate_maps_from_csv(csv_file, materials_folder, coordinates_file, construct_file, name_file, output_folder, font_path=None):
    """
    CSVファイルに基づいてマップを一括生成
    """
    
    os.makedirs(output_folder, exist_ok=True)
    
    print("データCSVファイルを読み込み中…")
    data_df = pd.read_csv(csv_file)
    
    print("座標CSVファイルを読み込み中…")
    coord_df = pd.read_csv(coordinates_file)
    coord_dict = {}
    for _, row in coord_df.iterrows():
        index_val = row.iloc[0]
        x_coord = row.iloc[7]
        y_coord = row.iloc[8]
        coord_dict[index_val] = (x_coord, y_coord)
    
    print("拠点情報CSVファイルを読み込み中…")
    construct_df = pd.read_csv(construct_file)
    
    # 名称マッピングファイルを読み込み
    print("名称マッピングファイルを読み込み中…")
    name_df = pd.read_csv(name_file,header=None)
    name_dict = {}
    for _, row in name_df.iterrows():
        name_dict[row.iloc[0]] = row.iloc[1]
    
    # 2つの辞書を作成し、特殊拠点と通常拠点をそれぞれ格納する
    special_construct_dict = {}  # 49410/49420/49430
    normal_construct_dict = {}   # その他の拠点
    
    for _, construct_row in construct_df.iterrows():
        map_id = construct_row.iloc[1]
        show_flag = construct_row.iloc[3]
        
        if show_flag == 1:
            construct_type = construct_row.iloc[2]
            coord_index = construct_row.iloc[4]
            
            # 特殊拠点判定
            if construct_type in [49410, 49420, 49430]:
                if map_id not in special_construct_dict:
                    special_construct_dict[map_id] = []
                special_construct_dict[map_id].append({
                    'type': construct_type,
                    'coord_index': coord_index
                })
            else:
                if map_id not in normal_construct_dict:
                    normal_construct_dict[map_id] = []
                normal_construct_dict[map_id].append({
                    'type': construct_type,
                    'coord_index': coord_index
                })
    
    # フォント読み込み、3種類のサイズのフォントを作成
    font_event = None
    font_night = None
    font_building = None
    
    if font_path and os.path.exists(font_path):
        try:
            font_event = ImageFont.truetype("Jiyucho.ttf", 160)  # 特殊イベント注記用フォント
            font_night = ImageFont.truetype("NotoSansJP-Medium.ttf", 95)  # night_circle注記用フォント
            font_building = ImageFont.truetype("NotoSansJP-Medium.ttf", 65)  # 拠点注記用フォント
            print(f"フォントの読み込みに成功しました: {font_path}")
        except Exception as e:
            font_event = ImageFont.load_default()
            font_night = ImageFont.load_default()
            font_building = ImageFont.load_default()
            print(f"指定フォントを読み込めませんでした {font_path}，デフォルトフォントを使用: {e}")
    else:
        font_event = ImageFont.load_default()
        font_night = ImageFont.load_default()
        font_building = ImageFont.load_default()
        print("デフォルトフォントを使用")
    
    night_circle_path = os.path.join(materials_folder, "night_circle.png")
    if not os.path.exists(night_circle_path):
        print(f"エラー：night_circle.pngが存在しません {night_circle_path}")
        return
    
    try:
        night_circle_img = Image.open(night_circle_path).convert('RGBA')
    except:
        print(f"エラー：night_circle.pngを読み込めません {night_circle_path}")
        return
    
    print("画像生成を開始…")
    for idx, row in data_df.iterrows():
        special_value = row['Special']
        background_path = os.path.join(materials_folder, f"background_{special_value}.png")
        
        if not os.path.exists(background_path):
            print(f"警告: 背景画像{background_path}が存在しないため、処理をスキップします")
            continue
            
        try:
            background = Image.open(background_path).convert('RGBA')
        except:
            print(f"エラー：背景画像 {background_path}を読み込めないため、処理をスキップします")
            continue
            
        draw = ImageDraw.Draw(background)
        
        # 特殊イベントをチェック - 列参照を修正（9列目EvPatFlagを使用）
        event_value = row['Event_30*0']
        if event_value == 3080:
            evpat_value = row['EvPatFlag']  # 9列目
            frenzy_path = os.path.join(materials_folder, f"Frenzy_{evpat_value}.png")
            if os.path.exists(frenzy_path):
                try:
                    frenzy_img = Image.open(frenzy_path).convert('RGBA')
                    # paste方式で特殊イベントアセットを合成
                    background.paste(frenzy_img, (0, 0), frenzy_img)
                    # drawオブジェクトを再作成
                    draw = ImageDraw.Draw(background)
                except Exception as e:
                    print(f"エラー：Frenzy画像を処理できません {frenzy_path}: {e}")
            else:
                print(f"警告: Frenzy画像が存在しません {frenzy_path}")
        
        # NightLordアセットを追加 - alpha_compositeを使用して透明度を正しく処理
        nightlord_value = row['NightLord']
        nightlord_path = os.path.join(materials_folder, f"nightlord_{nightlord_value}.png")
        if os.path.exists(nightlord_path):
            try:
                nightlord_img = Image.open(nightlord_path).convert('RGBA')
                # pasteではなくalpha_compositeを使用
                background = Image.alpha_composite(background, nightlord_img)
                # drawオブジェクトを再作成
                draw = ImageDraw.Draw(background)
            except Exception as e:
                print(f"エラー：NightLord画像を処理できません {nightlord_path}: {e}")
        else:
            print(f"警告: NightLord画像が存在しません {nightlord_path}")
        
        # Treasureアセットを追加 - alpha_compositeを使用
        treasure_value = row['Treasure_800']
        combined_value = treasure_value * 10 + special_value
        treasure_path = os.path.join(materials_folder, f"treasure_{combined_value}.png")
        if os.path.exists(treasure_path):
            try:
                treasure_img = Image.open(treasure_path).convert('RGBA')
                # pasteではなくalpha_compositeを使用
                background = Image.alpha_composite(background, treasure_img)
                # drawオブジェクトを再作成
                draw = ImageDraw.Draw(background)
            except Exception as e:
                print(f"エラー：Treasure画像を処理できません {treasure_path}: {e}")
        else:
            print(f"警告: Treasure画像が存在しません {treasure_path}")
        
        # RotRew_500アセットを追加 - 値が0の場合を除いて追加
        rotrew_value = row['RotRew_500']
        if rotrew_value != 0:  # 値が0の場合のみ処理
            rotrew_path = os.path.join(materials_folder, f"RotRew_{rotrew_value}.png")
            if os.path.exists(rotrew_path):
                try:
                    rotrew_img = Image.open(rotrew_path).convert('RGBA')
                    # alpha_compositeでレイヤーを結合
                    background = Image.alpha_composite(background, rotrew_img)
                    # drawオブジェクトを再作成
                    draw = ImageDraw.Draw(background)
                except Exception as e:
                    print(f"エラー：RotRew画像を処理できません {rotrew_path}: {e}")
            else:
                print(f"警告: RotRew画像が存在しません {rotrew_path}")
        
        # night_circleアセットを追加 - paste方式を使用
        day1_loc = row['Day1Loc']
        day1_boss = row['Day1Boss']
        day1_extra = row.iloc[14] if len(row) > 14 else -1  # 15列目
        
        day2_loc = row['Day2Loc']
        day2_boss = row['Day2Boss']
        day2_extra = row.iloc[15] if len(row) > 15 else -1  # 16列目
        
        # night_circleの文字情報を保存、後で描画
        night_circle_texts = []
        
        if day1_loc in coord_dict:
            x, y = coord_dict[day1_loc]
            x_pos = int(round(x - night_circle_img.width // 2))
            y_pos = int(round(y - night_circle_img.height // 2))
            # paste方式で重ね合わせ
            background.paste(night_circle_img, (x_pos, y_pos), night_circle_img)
            
            # night_circleのラベル文字情報を保存
            if day1_boss in name_dict:
                text = "DAY1 "+name_dict[day1_boss]
                # textsizeの代わりにgetbboxを使用
                bbox = font_night.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = int(round(x - text_width // 2))
                text_y = int(round(y - text_height // 2))
                
                night_circle_texts.append({
                    'text': text,
                    'position': (text_x, text_y),
                    'font': font_night
                })
                
                # 追加文字列を保存（15列目）
                if day1_extra != -1 and day1_extra in name_dict:
                    extra_text = name_dict[day1_extra]
                    bbox_extra = font_night.getbbox(extra_text)
                    extra_width = bbox_extra[2] - bbox_extra[0]
                    extra_height = bbox_extra[3] - bbox_extra[1]
                    extra_x = int(round(x - extra_width // 2))
                    extra_y = int(round(text_y + text_height + 5))  # メインテキストの下
                    
                    night_circle_texts.append({
                        'text': extra_text,
                        'position': (extra_x, extra_y),
                        'font': font_night
                    })
        else:
            print(f"警告: 座標 {day1_loc} は座標ファイルに存在しません")
        
        if day2_loc in coord_dict:
            x, y = coord_dict[day2_loc]
            x_pos = int(round(x - night_circle_img.width // 2))
            y_pos = int(round(y - night_circle_img.height // 2))
            # paste方式で重ね合わせ
            background.paste(night_circle_img, (x_pos, y_pos), night_circle_img)
            
            # night_circleのラベル文字情報を保存
            if day2_boss in name_dict:
                text = "DAY2 "+name_dict[day2_boss]
                # textsizeの代わりにgetbboxを使用
                bbox = font_night.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = int(round(x - text_width // 2))
                text_y = int(round(y - text_height // 2))
                
                night_circle_texts.append({
                    'text': text,
                    'position': (text_x, text_y),
                    'font': font_night
                })
                
                # 追加文字列を保存（16列目）
                if day2_extra != -1 and day2_extra in name_dict:
                    extra_text = name_dict[day2_extra]
                    bbox_extra = font_night.getbbox(extra_text)
                    extra_width = bbox_extra[2] - bbox_extra[0]
                    extra_height = bbox_extra[3] - bbox_extra[1]
                    extra_x = int(round(x - extra_width // 2))
                    extra_y = int(round(text_y + text_height + 5))  # メインテキストの下
                    
                    night_circle_texts.append({
                        'text': extra_text,
                        'position': (extra_x, extra_y),
                        'font': font_night
                    })
        else:
            print(f"警告: 座標 {day2_loc} は座標ファイルに存在しません")
        
        # 拠点アセットを追加 - まず特殊拠点を追加(49410/49420/49430)
        current_map_id = row['ID']
        
        # 拠点の文字情報を保存、後で描画
        building_texts = []
        
        # 特殊拠点を追加
        if current_map_id in special_construct_dict:
            for construct_info in special_construct_dict[current_map_id]:
                construct_type = construct_info['type']
                coord_index = construct_info['coord_index']
                
                if coord_index in coord_dict:
                    x, y = coord_dict[coord_index]
                    
                    construct_path = os.path.join(materials_folder, f"Construct_{construct_type}.png")
                    if os.path.exists(construct_path):
                        try:
                            construct_img = Image.open(construct_path).convert('RGBA')
                            # 位置を計算し、拠点アセットの中心が座標点に合うように配置
                            x_pos = int(round(x - construct_img.width // 2))
                            y_pos = int(round(y - construct_img.height // 2))
                            # paste方式で重ね合わせ
                            background.paste(construct_img, (x_pos, y_pos), construct_img)
                            
                            # 拠点のラベル文字情報を保存
                            if construct_type in name_dict:
                                text = name_dict[construct_type]
                                # textsizeの代わりにgetbboxを使用
                                bbox = font_building.getbbox(text)
                                text_width = bbox[2] - bbox[0]
                                text_height = bbox[3] - bbox[1]
                                text_x = int(round(x - text_width // 2))
                                text_y = int(round(y + construct_img.height // 2 + 10))  # 拠点の下
                                
                                building_texts.append({
                                    'text': text,
                                    'position': (text_x, text_y),
                                    'font': font_building
                                })
                        except Exception as e:
                            print(f"エラー：拠点画像を処理できません {construct_path}: {e}")
                    else:
                        print(f"警告: 拠点画像が存在しません {construct_path}")
                else:
                    print(f"警告: 座標インデクス {coord_index} は座標ファイルに存在しません")
        
        # 通常拠点を追加
        if current_map_id in normal_construct_dict:
            for construct_info in normal_construct_dict[current_map_id]:
                construct_type = construct_info['type']
                coord_index = construct_info['coord_index']
                
                if coord_index in coord_dict:
                    x, y = coord_dict[coord_index]
                    
                    construct_path = os.path.join(materials_folder, f"Construct_{construct_type}.png")
                    if os.path.exists(construct_path):
                        try:
                            construct_img = Image.open(construct_path).convert('RGBA')
                            # 位置を計算し、拠点アセットの中心が座標点に合うように配置
                            x_pos = int(round(x - construct_img.width // 2))
                            y_pos = int(round(y - construct_img.height // 2))
                            # paste方式で重ね合わせ
                            background.paste(construct_img, (x_pos, y_pos), construct_img)
                            
                            # 拠点のラベル文字情報を保存
                            if construct_type in name_dict:
                                text = name_dict[construct_type]
                                # textsizeの代わりにgetbboxを使用
                                bbox = font_building.getbbox(text)
                                text_width = bbox[2] - bbox[0]
                                text_height = bbox[3] - bbox[1]
                                text_x = int(round(x - text_width // 2))
                                text_y = int(round(y + construct_img.height // 2 + 10))  # 拠点の下
                                
                                building_texts.append({
                                    'text': text,
                                    'position': (text_x, text_y),
                                    'font': font_building
                                })
                        except Exception as e:
                            print(f"エラー：拠点画像を処理できません {construct_path}: {e}")
                    else:
                        print(f"警告: 拠点画像が存在しません {construct_path}")
                else:
                    print(f"警告: 座標インデクス {coord_index} は座標ファイルに存在しません")
        
        # Startアセットを追加 - 最上層に配置することを保証
        start_value = row['Start_190']
        start_path = os.path.join(materials_folder, f"Start_{start_value}.png")
        if os.path.exists(start_path):
            try:
                start_img = Image.open(start_path).convert('RGBA')
                # pasteではなくalpha_compositeを使用
                background = Image.alpha_composite(background, start_img)
                # drawオブジェクトを再作成
                draw = ImageDraw.Draw(background)
            except Exception as e:
                print(f"エラー：Start画像を処理できません {start_path}: {e}")
        else:
            print(f"警告: Start画像が存在しません {start_path}")
        
        # すべての文字を描画し、最前面に配置
        shadow_color1 = (255,255,255)
        shadow_color2 = (0,0,0)
        text_color = (255, 0, 0)  # 赤文字
                
        # night_circle文字を描画
        for text_info in night_circle_texts:
            text, position, font = text_info['text'], text_info['position'], text_info['font']
            x, y = position
            # 座標が画像範囲内にあるかを確認
            if 0 <= x < background.width and 0 <= y < background.height:
                # 文字に影を追加
                draw_narrow_text(background, (x-3, y-3), text, font=font, fill=shadow_color1, scale_x=0.60)
                draw_narrow_text(background, (x-1, y-1), text, font=font, fill=shadow_color1, scale_x=0.60)
                draw_narrow_text(background, (x+1, y+1), text, font=font, fill=shadow_color2, scale_x=0.60)
                draw_narrow_text(background, (x+3, y+3), text, font=font, fill=shadow_color2, scale_x=0.60)
                draw_narrow_text(background, (x+5, y+5), text, font=font, fill=shadow_color2, scale_x=0.60)
                draw_narrow_text(background, (x+7, y+7), text, font=font, fill=shadow_color2, scale_x=0.60)
                # 文字を追加
                draw_narrow_text(background, (x, y), text, font, fill=(120, 30, 240), scale_x=0.60)
        
        # 拠点文字を描画
        for text_info in building_texts:
            text, position, font = text_info['text'], text_info['position'], text_info['font']
            x, y = position
            # 座標が画像範囲内にあるかを確認
            if 0 <= x < background.width and 0 <= y < background.height:
                # 文字に影を追加
                draw_narrow_text(background, (x+4, y+4), text, font=font, fill=(0,0,0), scale_x=0.60)
                draw_narrow_text(background, (x-4, y-4), text, font=font, fill=(0,0,0), scale_x=0.60)
                # 文字を追加
                draw_narrow_text(background, (x, y), text, font, fill=(255, 255, 0), scale_x=0.60)
        
        # イベント説明の文字を追加
        event_flag = row['EventFlag']
        if event_flag in [7705, 7725]:
            # 特殊イベント7705と7725
            event_text = f"{name_dict.get(event_flag, event_flag)} {name_dict.get(event_value, event_value)}"
        else:
            event_text = f"{name_dict.get(event_flag, event_flag)}"
        
        # 指定位置へイベント説明テキストを追加
        event_x, event_y = int(round(1200)), int(round(4300))
        # getbboxを使用してテキストサイズを取得
        bbox = font_event.getbbox(event_text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 座標が画像範囲内にあるかを確認
        if 0 <= event_x < background.width and 0 <= event_y < background.height:
            print(f"イベント説明テキストを描画: {event_text}、位置: ({event_x}, {event_y})")
            # 文字に影を追加
            draw.text((event_x+15, event_y+15), event_text, font=font_event, fill=(115,15,230))
            # 文字を追加
            draw.text((event_x, event_y), event_text, font=font_event, fill=(255,255,255))
        else:
            print(f"警告: イベント説明テキスト座標 ({event_x}, {event_y}) が画像の範囲を超えています")
        
        # 画像を1/4サイズに縮小
        original_width, original_height = background.size
        new_size = (original_width // 5, original_height // 5)
        resized_background = background.resize(new_size, Image.Resampling.LANCZOS)
        
        # 画像を保存
        output_path = os.path.join(output_folder, f"map_{idx}.png")
        background.save(output_path)
        
        # カウントの出力を修正
        if (idx + 1) % 10 == 0:
            print(f"{idx + 1}枚の画像を生成しました…")
    
    print("すべての画像の生成が完了しました！")

if __name__ == "__main__":
    DATA_CSV_FILE = "MAP_PATTERN.csv"
    COORDINATES_CSV_FILE = "座標.csv"
    CONSTRUCT_CSV_FILE = "CONSTRUCT.csv"
    NAME_CSV_FILE = "NAME.csv"  # 名称マッピングファイルを新規追加
    MATERIALS_FOLDER = "assets"
    OUTPUT_FOLDER = "output"
    FONT_PATH = "NotoSansJP-Medium.ttf"  # フォントのパスを指定可能（例："arial.ttf"）
    
    generate_maps_from_csv(
        csv_file=DATA_CSV_FILE,
        materials_folder=MATERIALS_FOLDER,
        coordinates_file=COORDINATES_CSV_FILE,
        construct_file=CONSTRUCT_CSV_FILE,
        name_file=NAME_CSV_FILE,
        output_folder=OUTPUT_FOLDER,
        font_path=FONT_PATH
    )