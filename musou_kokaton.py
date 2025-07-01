import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score: int):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if key_lst[pg.K_RSHIFT] and score.value > 100:
            self.state = "hyper"
            self.hyper_life = 500
            score.value -= 100
        if self.hyper_life > 0:
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
        if self.hyper_life == 0:
            self.state = "normal"
        screen.blit(self.image, self.rect)


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 半透明
        self.image.fill((0, 0, 0))  # 黒
        self.rect = self.image.get_rect()
        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        """
        if self.state == "inactive":
            self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
            if check_bound(self.rect) != (True, True):
                self.kill()
            return
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()
            
class Shield(pg.sprite.Sprite):
    """防御壁"""
    def __init__(self, bird, life=400):
        super().__init__()
        # サイズ：幅20px × 高さ(こうかとん身長×2)
        w, h = 20, bird.rect.height * 2
        # 回転前の元画像を保持
        self.orig_image = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(self.orig_image, (0, 0, 255), (0, 0, w, h))
        # 向きに合わせて回転
        vx, vy = bird.dire
        deg = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotate(self.orig_image, deg)
        self.rect = self.image.get_rect()
        # こうかとん中心から一体分ずらした位置に配置
        offset = bird.rect.height
        self.rect.centerx = bird.rect.centerx + vx * offset
        self.rect.centery = bird.rect.centery + vy * offset
        # 発動時間（400フレーム）
        self.life = life
         
    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: int=0): # angle0引数を追加
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数 angle0：ビームの初期回転角度（度数法）
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        base_angle = math.degrees(math.atan2(-self.vy, self.vx))
        
        self.angle = base_angle + angle0 # angle0 を base_angle に加算

        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 1.0)
        self.vx = math.cos(math.radians(self.angle))
        self.vy = -math.sin(math.radians(self.angle))
        self.rect = self.image.get_rect()
        
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy * 0.5 
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx * 0.5
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 10000
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class NeoBeam:
    """
    複数ビームを生成・管理するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        複数ビーム生成の準備を行う
        引数1 bird: ビームを放つこうかとんのインスタンス
        引数2 num: 生成するビームの数
        """
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list[Beam]:
        """
        -50°～+50°の角度範囲で指定ビーム数のBeamインスタンスを生成し、リストにappendする
        戻り値: Beamインスタンスのリスト
        """
        beams = []
        if self.num == 1:
            # ビームが1本の場合、こうかとんの向きに合わせた角度0度で発射
            beams.append(Beam(self.bird, 0))
        elif self.num > 1:
            start_angle = -50
            end_angle = 50
            # ビームの間隔を均等にするためのステップ計算
            step = (end_angle - start_angle) / (self.num - 1)
            for i in range(self.num):
                angle = start_angle + i * step
                beams.append(Beam(self.bird, angle))
        return beams
class EMP:
    """
    電磁パルス(EMP)に関するクラス
    発動時に存在する敵機と爆弾を無効化し、画面全体に黄色の透明矩形を表示する
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        self.emys = emys
        self.bombs = bombs
        self.screen = screen
        self.overlay_time = 3  # 0.05秒×3フレームで表示（50fpsなら3フレームで約0.06秒）
        self.overlay_count = 0
        self.active = True  # 発動中フラグ

        # 敵機無効化処理
        for emy in self.emys:
            emy.interval = float("inf")  # 爆弾投下停止
            # ラプラシアンフィルタをかける
            emy.image = pg.transform.laplacian(emy.image)

        # 爆弾無効化処理
        for bomb in self.bombs:
            bomb.speed /= 2  # 速度半減
            bomb.state = "inactive"  # 新たにstate属性を追加し無効化を示す

    def update(self):
        """
        EMP発動時の画面全体に黄色の透明矩形を表示
        表示時間が過ぎると発動終了フラグを折る
        """
        if self.overlay_count < self.overlay_time:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            overlay.fill((255, 255, 0, 100))  # 黄色、透明度100/255
            self.screen.blit(overlay, (0, 0))
            self.overlay_count += 1
        else:
            self.active = False


def main():
    pg.init()
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    shields = pg.sprite.Group()  # 防御壁のグループ

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group() # 全てのビームを管理するグループ
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravitys = pg.sprite.Group()
    emp = None

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            
            # スペースキー単独でのビーム発射
            # 左Shiftキーが押されていないことを確認
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE and not key_lst[pg.K_LSHIFT]:
                beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                if score.value > 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(Shield(bird, life=400))
                    
            if event.type == pg.KEYDOWN and event.key == pg.K_q and score.value >= 200:
                gravitys.add(Gravity(400))
                score.value -= 200
            
            # 左Shiftキーを押しながらスペースキーで多方向ビーム発射
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE and key_lst[pg.K_LSHIFT]:
                # NeoBeamクラスのインスタンスを生成し、多方向ビームを取得
                neo_beam = NeoBeam(bird, 5) # ここで発射したいビームの本数を指定 (例: 5本)
                new_beams = neo_beam.gen_beams()
                # 生成された各ビームをbeamsグループに追加
                for beam in new_beams:
                    beams.add(beam)
                
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_e:
                    if score.value >= 20 and emp is None:
                        emp = EMP(emys, bombs, screen)
                        score.value -= 20
        screen.blit(bg_img, [0, 0])
        if emp is not None:
            emp.update()
            if not emp.active:
                emp = None
        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1
                continue
            bird.change_img(8, screen)
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return


        for bomb in pg.sprite.spritecollide(bird, bombs, False):
            if getattr(bomb, "state", "active") == "inactive":
                bomb.kill()
            else:
                bird.change_img(8, screen)
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return


        for g in gravitys:
            for bomb in pg.sprite.spritecollide(g, bombs, True):
                exps.add(Explosion(bomb, 50))
                score.value += 1
            for emy in pg.sprite.spritecollide(g, emys, True):
                exps.add(Explosion(emy, 100))
                score.value += 10

        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        shields.draw(screen) 
        shields.update()
        # 防御壁の更新と描画
        exps.update()
        exps.draw(screen)
        score.update(screen)
        hits = pg.sprite.groupcollide(bombs, shields, True, False)
        hits = pg.sprite.groupcollide(bombs, shields, True, False)
        for bomb, hit_ls in hits.items():
             exps.add(Explosion(bomb, 30))
        gravitys.update()
        gravitys.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()