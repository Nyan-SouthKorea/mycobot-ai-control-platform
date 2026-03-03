import os

path = './YOLO_train/Dice_ir/dataset'

for mode in ['train', 'val']:
    # label 새로 만들기
    os.makedirs(f'{path}/{mode}/labels_new', exist_ok=True)

    # 레이블 순회하며 문자를 숫자로 변경하기
    for label_name in os.listdir(f'{path}/{mode}/labels'):

        print(label_name)
        # 읽기
        with open(f'{path}/{mode}/labels/{label_name}', 'r', encoding='utf-8') as f:
            old_txt = f.read()
        new_txt = old_txt.replace('dice', '0')

        # 쓰기
        with open(f'{path}/{mode}/labels_new/{label_name}', 'w', encoding='utf-8') as f:
            f.write(new_txt)

