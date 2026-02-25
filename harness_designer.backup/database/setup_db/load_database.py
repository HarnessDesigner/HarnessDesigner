import math
import os
import json

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


splash = None


def _build_colors():
    return (
        (0, 'Black', 0x000000FF),
        (1, 'Brown', 0x8C7355FF),
        (2, 'Red', 0xFE0000FF),
        (3, 'Orange', 0xFFA500FF),
        (4, 'Yellow', 0xFFFF01FF),
        (5, 'Green', 0x28C629FF),
        (6, 'Blue', 0x0000FEFF),
        (7, 'Violet', 0x9400D4FF),
        (8, 'Gray', 0xA1A1A1FF),
        (9, 'White', 0xFFFFFFFF),
        (10, 'Absolute Zero', 0x0048BAFF),
        (11, 'Acid Green', 0xB0BF1AFF),
        (12, 'Alice Blue', 0xF0F8FFFF),
        (13, 'Alizarin crimson', 0xE32636FF),
        (14, 'Amaranth', 0xE52B50FF),
        (15, 'Amber', 0xFFBF00FF),
        (16, 'Amethyst', 0x9966CCFF),
        (17, 'Antique White', 0xFAEBD7FF),
        (18, 'Antique White1', 0xFFEFDBFF),
        (19, 'Antique White2', 0xEEDFCCFF),
        (20, 'Antique White3', 0xCDC0B0FF),
        (21, 'Antique White4', 0x8B8378FF),
        (22, 'Apricot', 0xFBCEB1FF),
        (23, 'Aqua', 0x00FFFFFF),
        (24, 'Aquamarine1', 0x7FFFD4FF),
        (25, 'Aquamarine2', 0x76EEC6FF),
        (26, 'Aquamarine4', 0x458B74FF),
        (27, 'Army Green', 0x4B5320FF),
        (28, 'Arylide Yellow', 0xE9D66BFF),
        (29, 'Ash Grey', 0xB2BEB5FF),
        (30, 'Asparagus', 0x87A96BFF),
        (31, 'Aureolin', 0xFDEE00FF),
        (32, 'Azure1', 0xF0FFFFFF),
        (33, 'Azure2', 0xE0EEEEFF),
        (34, 'Azure3', 0xC1CDCDFF),
        (35, 'Azure4', 0x838B8BFF),
        (36, 'Baby Blue', 0x89CFF0FF),
        (37, 'Baby Pink', 0xF4C2C2FF),
        (38, 'Baker-Miller Pink', 0xFF91AFFF),
        (39, 'Banana Mania', 0xFAE7B5FF),
        (40, 'Banana Yellow', 0xFFE135FF),
        (41, 'Barn Red', 0x7C0A02FF),
        (42, 'Battleship Gray', 0x848482FF),
        (43, 'Beaver', 0x9F8170FF),
        (44, 'Beige', 0xF5F5DCFF),
        (45, 'Bisque1', 0xFFE4C4FF),
        (46, 'Bisque2', 0xEED5B7FF),
        (47, 'Bisque3', 0xCDB79EFF),
        (48, 'Bisque4', 0x8B7D6BFF),
        (49, 'Bistre', 0x3D2B1FFF),
        (50, 'Bitter Lemon', 0xCAE00DFF),
        (51, 'Bitter Lime', 0xBFFF00FF),
        (52, 'Bittersweet', 0xFE6F5EFF),
        (53, 'Bittersweet Shimmer', 0xBF4F51FF),
        (54, 'Black Coffee', 0x3B2F2FFF),
        (55, 'Black Olive', 0x3B3C36FF),
        (56, 'Black Shadows', 0xBFAFB2FF),
        (57, 'Blanched Almond', 0xFFEBCDFF),
        (58, 'Bleu de France', 0x318CE7FF),
        (59, 'Blond', 0xFAF0BEFF),
        (60, 'Blue (Pantone)', 0x0018A8FF),
        (61, 'Blue Bell', 0xA2A2D0FF),
        (62, 'Blue Green', 0x0D98BAFF),
        (63, 'Blue1', 0x0000FFFF),
        (64, 'Blue2', 0x0000EEFF),
        (65, 'Dark Blue', 0x00008BFF),
        (66, 'Blue Violet', 0x8A2BE2FF),
        (67, 'Bole', 0x79443BFF),
        (68, 'Bone', 0xE3DAC9FF),
        (69, 'Boysenberry', 0x873260FF),
        (70, 'Brandeis Blue', 0x0070FFFF),
        (71, 'Brass', 0xB5A642FF),
        (72, 'Brick Red', 0xCB4154FF),
        (73, 'Bright Cerulean', 0x1DACD6FF),
        (74, 'Bright Green', 0x66FF00FF),
        (75, 'Bright Lavender', 0xBF94E4FF),
        (76, 'Bright Lilac', 0xD891EFFF),
        (77, 'Bright Maroon', 0xC32148FF),
        (78, 'Bright Navy Blue', 0x1974D2FF),
        (79, 'Bright Turquoise', 0x08E8DEFF),
        (80, 'Bright Ube', 0xD19FE8FF),
        (81, 'Brilliant Rose', 0xFF55A3FF),
        (82, 'Brink Pink', 0xFB607FFF),
        (83, 'British Racing Green', 0x004225FF),
        (84, 'Bronze', 0xCD7F32FF),
        (85, 'Brown1', 0xFF4040FF),
        (86, 'Brown2', 0xEE3B3BFF),
        (87, 'Brown3', 0xCD3333FF),
        (88, 'Brown4', 0x8B2323FF),
        (89, 'Brunswick Green', 0x1B4D3EFF),
        (90, 'Bubble Gum', 0xFFC1CCFF),
        (91, 'Buff', 0xF0DC82FF),
        (92, 'Bulgarian Rose', 0x480607FF),
        (93, 'Burgundy', 0x800020FF),
        (94, 'Burlywood', 0xDEB887FF),
        (95, 'Burlywood1', 0xFFD39BFF),
        (96, 'Burlywood2', 0xEEC591FF),
        (97, 'Burlywood3', 0xCDAA7DFF),
        (98, 'Burlywood4', 0x8B7355FF),
        (99, 'Burnished Brown', 0xA17A74FF),
        (100, 'Burnt Orange', 0xCC5500FF),
        (101, 'Burnt Sienna', 0xE97451FF),
        (102, 'Burnt Umber', 0x8A3324FF),
        (103, 'Byzantine', 0xBD33A4FF),
        (104, 'Byzantium', 0x702963FF),
        (105, 'Cadet Grey', 0x91A3B0FF),
        (106, 'Cadet Blue', 0x5F9EA0FF),
        (107, 'Cadet Blue1', 0x98F5FFFF),
        (108, 'Cadet Blue2', 0x8EE5EEFF),
        (109, 'Cadet Blue3', 0x7AC5CDFF),
        (110, 'Cadet Blue4', 0x53868BFF),
        (111, 'Cadmium Green', 0x006B3CFF),
        (112, 'Cadmium Orange', 0xED872DFF),
        (113, 'Cadmium Red', 0xE30022FF),
        (114, 'Cadmium Yellow', 0xFFF600FF),
        (115, 'Cambridge Blue', 0xA3C1ADFF),
        (116, 'Camel', 0xC19A6BFF),
        (117, 'Cameo Pink', 0xEFBBCCFF),
        (118, 'Camouflage Green', 0x78866BFF),
        (119, 'Canary', 0xFFFF99FF),
        (120, 'Canary Yellow', 0xFFEF00FF),
        (121, 'Candy Apple Red', 0xFF0800FF),
        (122, 'Candy Pink', 0xE4717AFF),
        (123, 'Caput Mortuum', 0x592720FF),
        (124, 'Cardinal', 0xC41E3AFF),
        (125, 'Caribbean Green', 0x00CC99FF),
        (126, 'Carmine', 0x960018FF),
        (127, 'Carmine Pink', 0xEB4C42FF),
        (128, 'Carnation Pink', 0xFFA6C9FF),
        (129, 'Carnelian', 0xB31B1BFF),
        (130, 'Carolina Blue', 0x56A0D3FF),
        (131, 'Carrot Orange', 0xED9121FF),
        (132, 'Castleton Green', 0x00563FFF),
        (133, 'Cedar Chest', 0xC95A49FF),
        (134, 'Celadon', 0xACE1AFFF),
        (135, 'Celadon Green', 0x2F847CFF),
        (136, 'Celeste', 0xB2FFFFFF),
        (137, 'Celtic Blue', 0x246BCEFF),
        (138, 'Cerise', 0xDE3163FF),
        (139, 'Cerulean', 0x007BA7FF),
        (140, 'Cerulean Blue', 0x2A52BEFF),
        (141, 'Cerulean Frost', 0x6D9BC3FF),
        (142, 'Cg Blue', 0x007AA5FF),
        (143, 'Chamoisee', 0xA0785AFF),
        (144, 'Champagne', 0xF7E7CEFF),
        (145, 'Charcoal', 0x36454FFF),
        (146, 'Chartreuse1', 0x7FFF00FF),
        (147, 'Chartreuse2', 0x76EE00FF),
        (148, 'Chartreuse3', 0x66CD00FF),
        (149, 'Chartreuse4', 0x458B00FF),
        (150, 'Cherry Blossom Pink', 0xFFB7C5FF),
        (151, 'Chestnut', 0x954535FF),
        (152, 'Chocolate', 0xD2691EFF),
        (153, 'Chocolate1', 0xFF7F24FF),
        (154, 'Chocolate2', 0xEE7621FF),
        (155, 'Chocolate3', 0xCD661DFF),
        (156, 'Chrome Yellow', 0xFFA700FF),
        (157, 'Cinereous', 0x98817BFF),
        (158, 'Cinnabar', 0xE34234FF),
        (159, 'Citrine', 0xE4D00AFF),
        (160, 'Citron', 0x9FA91FFF),
        (161, 'Claret', 0x7F1734FF),
        (162, 'Cobalt', 0x0047ABFF),
        (163, 'Coffee', 0x6F4E37FF),
        (164, 'Cool Grey', 0x8C92ACFF),
        (165, 'Copper', 0xB87333FF),
        (166, 'Copper Red', 0xCB6D51FF),
        (167, 'Copper Rose', 0x996666FF),
        (168, 'Coquelicot', 0xFF3800FF),
        (169, 'Coral', 0xFF7F50FF),
        (170, 'Coral Pink', 0xF88379FF),
        (171, 'Coral1', 0xFF7256FF),
        (172, 'Coral2', 0xEE6A50FF),
        (173, 'Coral3', 0xCD5B45FF),
        (174, 'Coral4', 0x8B3E2FFF),
        (175, 'Cordovan', 0x893F45FF),
        (176, 'Corn', 0xFBEC5DFF),
        (177, 'Cornflower Blue', 0x6495EDFF),
        (178, 'Cornsilk', 0xFFF8DCFF),
        (179, 'Cornsilk1', 0xEEE8CDFF),
        (180, 'Cornsilk2', 0xCDC8B1FF),
        (181, 'Cornsilk3', 0x8B8878FF),
        (182, 'Cosmic Cobalt', 0x2E2D88FF),
        (183, 'Cosmic Latte', 0xFFF8E7FF),
        (184, 'Cotton Candy', 0xFFBCD9FF),
        (185, 'Cream', 0xFFFDD0FF),
        (186, 'Crimson', 0xDC143CFF),
        (187, 'Crystal', 0xA7D8DEFF),
        (188, 'Cyan1', 0x00FFFFFF),
        (189, 'Cyan2', 0x00EEEEFF),
        (190, 'Cyan3', 0x00CDCDFF),
        (191, 'Cyan4', 0x008B8BFF),
        (192, 'Cyclamen', 0xF56FA1FF),
        (193, 'Daffodil', 0xFFFF31FF),
        (194, 'Dandelion', 0xF0E130FF),
        (195, 'Dark Brown', 0x654321FF),
        (196, 'Dark Byzantium', 0x5D3954FF),
        (197, 'Dark Jungle Green', 0x1A2421FF),
        (198, 'Dark Lavender', 0x734F96FF),
        (199, 'Dark Moss Green', 0x4A5D23FF),
        (200, 'Dark Pastel Green', 0x03C03CFF),
        (201, 'Dark Sienna', 0x3C1414FF),
        (202, 'Dark Sky Blue', 0x8CBED6FF),
        (203, 'Dark Spring Green', 0x177245FF),
        (204, 'Dark Goldenrod', 0xB8860BFF),
        (205, 'Dark Goldenrod1', 0xFFB90FFF),
        (206, 'Dark Goldenrod2', 0xEEAD0EFF),
        (207, 'Dark Goldenrod3', 0xCD950CFF),
        (208, 'Dark Goldenrod4', 0x8B6508FF),
        (209, 'Dark Green', 0x006400FF),
        (210, 'Dark Khaki', 0xBDB76BFF),
        (211, 'Dark Olive Green', 0x556B2FFF),
        (212, 'Dark Olive Green1', 0xCAFF70FF),
        (213, 'Dark Olive Green2', 0xBCEE68FF),
        (214, 'Dark Olive Green3', 0xA2CD5AFF),
        (215, 'Dark Olive Green4', 0x6E8B3DFF),
        (216, 'Dark Orange', 0xFF8C00FF),
        (217, 'Dark Orange1', 0xFF7F00FF),
        (218, 'Dark Orange2', 0xEE7600FF),
        (219, 'Dark Orange3', 0xCD6600FF),
        (220, 'Dark Orange4', 0x8B4500FF),
        (221, 'Dark Orchid', 0x9932CCFF),
        (222, 'Dark Orchid1', 0xBF3EFFFF),
        (223, 'Dark Orchid2', 0xB23AEEFF),
        (224, 'Dark Orchid3', 0x9A32CDFF),
        (225, 'Dark Orchid4', 0x68228BFF),
        (226, 'Dark Salmon', 0xE9967AFF),
        (227, 'Dark Sea Green', 0x8FBC8FFF),
        (228, 'Dark Sea Green1', 0xC1FFC1FF),
        (229, 'Dark Sea Green2', 0xB4EEB4FF),
        (230, 'Dark Sea Green3', 0x9BCD9BFF),
        (231, 'Dark Sea Green4', 0x698B69FF),
        (232, 'Dark Slate Blue', 0x483D8BFF),
        (233, 'Dark Slate Gray', 0x2F4F4FFF),
        (234, 'Dark Slate Gray1', 0x97FFFFFF),
        (235, 'Dark Slate Gray2', 0x8DEEEEFF),
        (236, 'Dark Slate Gray3', 0x79CDCDFF),
        (237, 'Dark Slate Gray4', 0x528B8BFF),
        (238, 'Dark Turquoise', 0x00CED1FF),
        (239, 'Dark Violet', 0x9400D3FF),
        (240, 'Dartmouth Green', 0x00703CFF),
        (241, 'Deep Cerise', 0xDA3287FF),
        (242, 'Deep Champagne', 0xFAD6A5FF),
        (243, 'Deep Fuchsia', 0xC154C1FF),
        (244, 'Deep Jungle Green', 0x004B49FF),
        (245, 'Deep Peach', 0xFFCBA4FF),
        (246, 'Deep Saffron', 0xFF9933FF),
        (247, 'Deep Space Sparkle', 0x4A646CFF),
        (248, 'Deep chestnut', 0xB94E48FF),
        (249, 'Deep Pink', 0xFF1493FF),
        (250, 'Deep Pink1', 0xEE1289FF),
        (251, 'Deep Pink2', 0xCD1076FF),
        (252, 'Deep Pink3', 0x8B0A50FF),
        (253, 'Deep Sky Blue', 0x00BFFFFF),
        (254, 'Deep Sky Blue1', 0x00B2EEFF),
        (255, 'Deep Sky Blue2', 0x009ACDFF),
        (256, 'Deep Sky Blue3', 0x00688BFF),
        (257, 'Denim', 0x1560BDFF),
        (258, 'Denim Blue', 0x2243B6FF),
        (259, 'Desert Sand', 0xEDC9AFFF),
        (260, 'Dim Gray', 0x696969FF),
        (261, 'Dodger Blue1', 0x1E90FFFF),
        (262, 'Dodger Blue2', 0x1C86EEFF),
        (263, 'Dodger Blue3', 0x1874CDFF),
        (264, 'Dodger Blue4', 0x104E8BFF),
        (265, 'Dogwood Rose', 0xD71868FF),
        (266, 'Dutch White', 0xEFDFBBFF),
        (267, 'Earth Yellow', 0xE1A95FFF),
        (268, 'Ebony', 0x555D50FF),
        (269, 'Eggplant', 0x614051FF),
        (270, 'Eggshell', 0xF0EAD6FF),
        (271, 'Egyptian Blue', 0x1034A6FF),
        (272, 'Electric Blue', 0x7DF9FFFF),
        (273, 'Electric Indigo', 0x6F00FFFF),
        (274, 'Electric Lime', 0xCCFF00FF),
        (275, 'Electric Purple', 0xBF00FFFF),
        (276, 'Emerald', 0x50C878FF),
        (277, 'Eminence', 0x6C3082FF),
        (278, 'Eton Blue', 0x96C8A2FF),
        (279, 'Falu Red', 0x801818FF),
        (280, 'Fawn', 0xE5AA70FF),
        (281, 'Feldgrau', 0x4D5D53FF),
        (282, 'Fern Green', 0x4F7942FF),
        (283, 'Ferrari Red', 0xFF2800FF),
        (284, 'Fire Opal', 0xE95C4BFF),
        (285, 'Firebrick', 0xB22222FF),
        (286, 'Firebrick1', 0xFF3030FF),
        (287, 'Firebrick2', 0xEE2C2CFF),
        (288, 'Firebrick3', 0xCD2626FF),
        (289, 'Firebrick4', 0x8B1A1AFF),
        (290, 'Flamingo Pink', 0xFC8EACFF),
        (291, 'Floral White', 0xFFFAF0FF),
        (292, 'Flourescent Blue', 0x15F4EEFF),
        (293, 'Forest Green', 0x228B22FF),
        (294, 'Forest Green1', 0x228B22FF),
        (295, 'French Beige', 0xA67B5BFF),
        (296, 'French Bistre', 0x856D4DFF),
        (297, 'French Blue', 0x0072BBFF),
        (298, 'French Lilac', 0x86608EFF),
        (299, 'French Mauve', 0xD473D4FF),
        (300, 'French Pink', 0xFD6C9EFF),
        (301, 'French Rose', 0xF64A8AFF),
        (302, 'French Sky Blue', 0x77B5FEFF),
        (303, 'French Violet', 0x8806CEFF),
        (304, 'Frostbite', 0xE936A7FF),
        (305, 'Fuchsia Purple', 0xCC397BFF),
        (306, 'Fuchsia Rose', 0xC74375FF),
        (307, 'Fulvous', 0xE48400FF),
        (308, 'Fuzzy Wuzzy', 0x87421FFF),
        (309, 'GO Green', 0x00AB66FF),
        (310, 'Gainsboro', 0xDCDCDCFF),
        (311, 'Gamboge', 0xE49B0FFF),
        (312, 'Generic Viridian', 0x007F66FF),
        (313, 'Ghost White', 0xF8F8FFFF),
        (314, 'Ginger', 0xB06500FF),
        (315, 'Glaucous', 0x6082B6FF),
        (316, 'Glossy Grape', 0xAB92B3FF),
        (317, 'Gold Fusion', 0x85754EFF),
        (318, 'Gold', 0xFFD700FF),
        (319, 'Gold2', 0xEEC900FF),
        (320, 'Gold3', 0xCDAD00FF),
        (321, 'Gold4', 0x8B7500FF),
        (322, 'Golden Brown', 0x996515FF),
        (323, 'Golden Poppy', 0xFCC200FF),
        (324, 'Golden Yellow', 0xFFDF00FF),
        (325, 'Goldenrod', 0xDAA520FF),
        (326, 'Goldenrod1', 0xFFC125FF),
        (327, 'Goldenrod2', 0xEEB422FF),
        (328, 'Goldenrod3', 0xCD9B1DFF),
        (329, 'Goldenrod4', 0x8B6914FF),
        (330, 'Granite Gray', 0x676767FF),
        (331, 'Granny Smith Apple', 0xA8E4A0FF),
        (332, 'Gray1', 0x030303FF),
        (333, 'Gray10', 0x1A1A1AFF),
        (334, 'Gray11', 0x1C1C1CFF),
        (335, 'Gray12', 0x1F1F1FFF),
        (336, 'Gray13', 0x212121FF),
        (337, 'Gray14', 0x242424FF),
        (338, 'Gray15', 0x262626FF),
        (339, 'Gray16', 0x292929FF),
        (340, 'Gray17', 0x2B2B2BFF),
        (341, 'Gray18', 0x2E2E2EFF),
        (342, 'Gray19', 0x303030FF),
        (343, 'Gray2', 0x050505FF),
        (344, 'Gray20', 0x333333FF),
        (345, 'Gray21', 0x363636FF),
        (346, 'Gray22', 0x383838FF),
        (347, 'Gray23', 0x3B3B3BFF),
        (348, 'Gray24', 0x3D3D3DFF),
        (349, 'Gray25', 0x404040FF),
        (350, 'Gray26', 0x424242FF),
        (351, 'Gray27', 0x454545FF),
        (352, 'Gray28', 0x474747FF),
        (353, 'Gray29', 0x4A4A4AFF),
        (354, 'Gray3', 0x080808FF),
        (355, 'Gray30', 0x4D4D4DFF),
        (356, 'Gray31', 0x4F4F4FFF),
        (357, 'Gray32', 0x525252FF),
        (358, 'Gray33', 0x545454FF),
        (359, 'Gray34', 0x575757FF),
        (360, 'Gray35', 0x595959FF),
        (361, 'Gray36', 0x5C5C5CFF),
        (362, 'Gray37', 0x5E5E5EFF),
        (363, 'Gray38', 0x616161FF),
        (364, 'Dark Gray', 0x636363FF),
        (365, 'Jet Black', 0x0A0A0AFF),
        (366, 'Gray40', 0x666666FF),
        (367, 'Gray41', 0x696969FF),
        (368, 'Gray42', 0x6B6B6BFF),
        (369, 'Gray43', 0x6E6E6EFF),
        (370, 'Gray44', 0x707070FF),
        (371, 'Gray45', 0x737373FF),
        (372, 'Gray46', 0x757575FF),
        (373, 'Gray47', 0x787878FF),
        (374, 'Gray48', 0x7A7A7AFF),
        (375, 'Gray49', 0x7D7D7DFF),
        (376, 'Gray5', 0x0D0D0DFF),
        (377, 'Gray50', 0x7F7F7FFF),
        (378, 'Gray51', 0x828282FF),
        (379, 'Gray52', 0x858585FF),
        (380, 'Gray53', 0x878787FF),
        (381, 'Gray54', 0x8A8A8AFF),
        (382, 'Gray55', 0x8C8C8CFF),
        (383, 'Gray56', 0x8F8F8FFF),
        (384, 'Tin', 0x919191FF),
        (385, 'Gray58', 0x949494FF),
        (386, 'Gray59', 0x969696FF),
        (387, 'Gray6', 0x0F0F0FFF),
        (388, 'Gray60', 0x999999FF),
        (389, 'Gray61', 0x9C9C9CFF),
        (390, 'Gray62', 0x9E9E9EFF),
        (391, 'Gray63', 0xA1A1A1FF),
        (392, 'Gray64', 0xA3A3A3FF),
        (393, 'Gray65', 0xA6A6A6FF),
        (394, 'Gray66', 0xA8A8A8FF),
        (395, 'Gray67', 0xABABABFF),
        (396, 'Gray68', 0xADADADFF),
        (397, 'Gray69', 0xB0B0B0FF),
        (398, 'Gray7', 0x121212FF),
        (399, 'Gray70', 0xB3B3B3FF),
        (400, 'Gray71', 0xB5B5B5FF),
        (401, 'Gray72', 0xB8B8B8FF),
        (402, 'Gray73', 0xBABABAFF),
        (403, 'Gray74', 0xBDBDBDFF),
        (404, 'Gray75', 0xBFBFBFFF),
        (405, 'Gray76', 0xC2C2C2FF),
        (406, 'Gray77', 0xC4C4C4FF),
        (407, 'Gray78', 0xC7C7C7FF),
        (408, 'Gray79', 0xC9C9C9FF),
        (409, 'Gray8', 0x141414FF),
        (410, 'Gray80', 0xCCCCCCFF),
        (411, 'Gray81', 0xCFCFCFFF),
        (412, 'Gray82', 0xD1D1D1FF),
        (413, 'Gray83', 0xD4D4D4FF),
        (414, 'Gray84', 0xD6D6D6FF),
        (415, 'Gray85', 0xD9D9D9FF),
        (416, 'Gray86', 0xDBDBDBFF),
        (417, 'Gray87', 0xDEDEDEFF),
        (418, 'Gray88', 0xE0E0E0FF),
        (419, 'Gray89', 0xE3E3E3FF),
        (420, 'Gray9', 0x171717FF),
        (421, 'Gray90', 0xE5E5E5FF),
        (422, 'Gray91', 0xE8E8E8FF),
        (423, 'Gray92', 0xEBEBEBFF),
        (424, 'Gray93', 0xEDEDEDFF),
        (425, 'Gray94', 0xF0F0F0FF),
        (426, 'Gray95', 0xF2F2F2FF),
        (427, 'Gray97', 0xF7F7F7FF),
        (428, 'Gray98', 0xFAFAFAFF),
        (429, 'Gray99', 0xFCFCFCFF),
        (430, 'Green (Crayola)', 0x1CAC78FF),
        (431, 'Green (Pantone)', 0x00AD43FF),
        (432, 'Green (Pigment)', 0x00A550FF),
        (433, 'Green Lizard', 0xA7F432FF),
        (434, 'Green Sheen', 0x6EAEA1FF),
        (435, 'Green1', 0x00FF00FF),
        (436, 'Green2', 0x00EE00FF),
        (437, 'Green3', 0x00CD00FF),
        (438, 'Green4', 0x008B00FF),
        (439, 'Green Yellow', 0xADFF2FFF),
        (440, 'Grullo', 0xA99A86FF),
        (441, 'Gunmetal', 0x2A3439FF),
        (442, 'Han Blue', 0x446CCFFF),
        (443, 'Han Purple', 0x5218FAFF),
        (444, 'Harlequin', 0x3FFF00FF),
        (445, 'Harvest Gold', 0xDA9100FF),
        (446, 'Heliotrope', 0xDF73FFFF),
        (447, 'Hollywood Cerise', 0xF400A1FF),
        (448, 'Honeydew1', 0xF0FFF0FF),
        (449, 'Honeydew2', 0xE0EEE0FF),
        (450, 'Honeydew3', 0xC1CDC1FF),
        (451, 'Honeydew4', 0x838B83FF),
        (452, 'Honolulu Blue', 0x006DB0FF),
        (453, 'Hot Magenta', 0xFF1DCEFF),
        (454, 'Hot Pink', 0xFF69B4FF),
        (455, 'Hot Pink1', 0xFF6EB4FF),
        (456, 'Hot Pink2', 0xEE6AA7FF),
        (457, 'Hot Pink3', 0xCD6090FF),
        (458, 'Hot Pink4', 0x8B3A62FF),
        (459, 'Hunter Green', 0x355E3BFF),
        (460, 'Iceberg', 0x71A6D2FF),
        (461, 'Icterine', 0xFCF75EFF),
        (462, 'Illuminating Emerald', 0x319177FF),
        (463, 'Imperial Red', 0xED2939FF),
        (464, 'Inchworm', 0xB2EC5DFF),
        (465, 'India Green', 0x138808FF),
        (466, 'Indian Yellow', 0xE3A857FF),
        (467, 'Indian Red', 0xCD5C5CFF),
        (468, 'Indian Red1', 0xFF6A6AFF),
        (469, 'Indian Red2', 0xEE6363FF),
        (470, 'Indian Red3', 0xCD5555FF),
        (471, 'Indian Red4', 0x8B3A3AFF),
        (472, 'Indigo', 0x4B0082FF),
        (473, 'International Orange', 0xFF4F00FF),
        (474, 'Iris', 0x5A4FCFFF),
        (475, 'Isabelline', 0xF4F0ECFF),
        (476, 'Ivory1', 0xFFFFF0FF),
        (477, 'Ivory2', 0xEEEEE0FF),
        (478, 'Ivory3', 0xCDCDC1FF),
        (479, 'Ivory4', 0x8B8B83FF),
        (480, 'Jade', 0x00A86BFF),
        (481, 'Japanese Carmine', 0x9D2933FF),
        (482, 'Jasmine', 0xF8DE7EFF),
        (483, 'Jazzberry Jam', 0xA50B5EFF),
        (484, 'Jonquil', 0xF4CA16FF),
        (485, 'Jungle Green', 0x29AB87FF),
        (486, 'Kelly Green', 0x4CBB17FF),
        (487, 'Keppel', 0x3AB09EFF),
        (488, 'Key Lime', 0xE8F48CFF),
        (489, 'Khaki', 0xF0E68CFF),
        (490, 'Khaki1', 0xFFF68FFF),
        (491, 'Khaki2', 0xEEE685FF),
        (492, 'Khaki3', 0xCDC673FF),
        (493, 'Khaki4', 0x8B864EFF),
        (494, 'Kombu Green', 0x354230FF),
        (495, 'Languid Lavender', 0xD6CADDFF),
        (496, 'Lapis Lazuli', 0x26619CFF),
        (497, 'Laser Lemon', 0xFFFF66FF),
        (498, 'Laurel Green', 0xA9BA9DFF),
        (499, 'Lavender', 0xE6E6FAFF),
        (500, 'Lavender (Floral)', 0xB57EDCFF),
        (501, 'Lavender Blue', 0xCCCCFFFF),
        (502, 'Lavender Gray', 0xC4C3D0FF),
        (503, 'Lavender Blush1', 0xFFF0F5FF),
        (504, 'Lavender Blush2', 0xEEE0E5FF),
        (505, 'Lavender Blush3', 0xCDC1C5FF),
        (506, 'Lavender Blush4', 0x8B8386FF),
        (507, 'Lawn Green', 0x7CFC00FF),
        (508, 'Lemon', 0xFFF700FF),
        (509, 'Lemon Curry', 0xCCA01DFF),
        (510, 'Lemon Glacier', 0xFDFF00FF),
        (511, 'Lemon Meringue', 0xF6EABEFF),
        (512, 'Lemon Yellow', 0xFFF44FFF),
        (513, 'Lemon Chiffon1', 0xFFFACDFF),
        (514, 'Lemon Chiffon2', 0xEEE9BFFF),
        (515, 'Lemon Chiffon3', 0xCDC9A5FF),
        (516, 'Lemon Chiffon4', 0x8B8970FF),
        (517, 'Light', 0xEEDD82FF),
        (518, 'Light Cornflower Blue', 0x93CCEAFF),
        (519, 'Light French Beige', 0xC8AD7FFF),
        (520, 'Light Orange', 0xFED8B1FF),
        (521, 'Light Periwinkle', 0xC5CBE1FF),
        (522, 'Light Blue', 0x90D5FFFF),
        (523, 'Light Blue1', 0xBFEFFFFF),
        (524, 'Light Blue2', 0xB2DFEEFF),
        (525, 'Light Blue3', 0x9AC0CDFF),
        (526, 'Light Blue4', 0x68838BFF),
        (527, 'Light Coral', 0xF08080FF),
        (528, 'Light Cyan1', 0xE0FFFFFF),
        (529, 'Light Cyan2', 0xD1EEEEFF),
        (530, 'Light Cyan3', 0xB4CDCDFF),
        (531, 'Light Cyan4', 0x7A8B8BFF),
        (532, 'Light Goldenrod1', 0xFFEC8BFF),
        (533, 'Light Goldenrod2', 0xEEDC82FF),
        (534, 'Light Goldenrod3', 0xCDBE70FF),
        (535, 'Light Goldenrod4', 0x8B814CFF),
        (536, 'Light GoldenrodYellow', 0xFAFAD2FF),
        (537, 'Light Gray', 0xD3D3D3FF),
        (538, 'Light Pink', 0xFFB6C1FF),
        (539, 'Light Pink1', 0xFFAEB9FF),
        (540, 'Light Pink2', 0xEEA2ADFF),
        (541, 'Light Pink3', 0xCD8C95FF),
        (542, 'Light Pink4', 0x8B5F65FF),
        (543, 'Light Salmon1', 0xFFA07AFF),
        (544, 'Light Salmon2', 0xEE9572FF),
        (545, 'Light Salmon3', 0xCD8162FF),
        (546, 'Light Salmon4', 0x8B5742FF),
        (547, 'Light SeaGreen', 0x20B2AAFF),
        (548, 'Light SkyBlue', 0x87CEFAFF),
        (549, 'Light SkyBlue1', 0xB0E2FFFF),
        (550, 'Light SkyBlue2', 0xA4D3EEFF),
        (551, 'Light SkyBlue3', 0x8DB6CDFF),
        (552, 'Light SkyBlue4', 0x607B8BFF),
        (553, 'Light SlateBlue', 0x8470FFFF),
        (554, 'Light SlateGray', 0x778899FF),
        (555, 'Light SteelBlue', 0xB0C4DEFF),
        (556, 'Light SteelBlue1', 0xCAE1FFFF),
        (557, 'Light SteelBlue2', 0xBCD2EEFF),
        (558, 'Light SteelBlue3', 0xA2B5CDFF),
        (559, 'Light SteelBlue4', 0x6E7B8BFF),
        (560, 'Light Yellow1', 0xFFFFE0FF),
        (561, 'Light Yellow2', 0xEEEED1FF),
        (562, 'Light Yellow3', 0xCDCDB4FF),
        (563, 'Light Yellow4', 0x8B8B7AFF),
        (564, 'Lilac', 0xC8A2C8FF),
        (565, 'Lilac Luster', 0xAE98AAFF),
        (566, 'Lime Green', 0x32CD32FF),
        (567, 'Lincoln Green', 0x195905FF),
        (568, 'Linen', 0xFAF0E6FF),
        (569, 'Little Boy Blue', 0x6CA0DCFF),
        (570, 'MSU Green', 0x18453BFF),
        (571, 'Macaroni and Cheese', 0xFFBD88FF),
        (572, 'Madder Lake', 0xCC3336FF),
        (573, 'Magenta', 0xFF00FFFF),
        (574, 'Magenta (Crayola)', 0xF653A6FF),
        (575, 'Magenta (Pantone)', 0xD0417EFF),
        (576, 'Magenta Haze', 0x9F4576FF),
        (577, 'Magenta2', 0xEE00EEFF),
        (578, 'Magenta3', 0xCD00CDFF),
        (579, 'Magenta4', 0x8B008BFF),
        (580, 'Magic Mint', 0xAAF0D1FF),
        (581, 'Mahogany', 0xC04000FF),
        (582, 'Majorelle Blue', 0x6050DCFF),
        (583, 'Malachite', 0x0BDA51FF),
        (584, 'Manatee', 0x979AAAFF),
        (585, 'Mandarin', 0xF37A48FF),
        (586, 'Mango', 0xFDBE02FF),
        (587, 'Mango Tango', 0xFF8243FF),
        (588, 'Mantis', 0x74C365FF),
        (589, 'Marigold', 0xEAA221FF),
        (590, 'Maroon', 0xB03060FF),
        (591, 'Maroon1', 0xFF34B3FF),
        (592, 'Maroon2', 0xEE30A7FF),
        (593, 'Maroon3', 0xCD2990FF),
        (594, 'Maroon4', 0x8B1C62FF),
        (595, 'Mauve', 0xE0B0FFFF),
        (596, 'Mauve Taupe', 0x915F6DFF),
        (597, 'Mauvelous', 0xEF98AAFF),
        (598, 'Maximum Blue Green', 0x30BFBFFF),
        (599, 'Maximum Blue Purple', 0xACACE6FF),
        (600, 'Maximum Green', 0x5E8C31FF),
        (601, 'Maximum Blue', 0x47ABCCFF),
        (602, 'May Green', 0x4C9141FF),
        (603, 'Maya Blue', 0x73C2FBFF),
        (604, 'Medium', 0x66CDAAFF),
        (605, 'Medium Aquamarine', 0x66DDAAFF),
        (606, 'Medium Candy Apple Red', 0xE2062CFF),
        (607, 'Medium Carmine', 0xAF4035FF),
        (608, 'Medium Champagne', 0xF3E5ABFF),
        (609, 'Medium Orchid', 0xBA55D3FF),
        (610, 'Medium Orchid1', 0xE066FFFF),
        (611, 'Medium Orchid2', 0xD15FEEFF),
        (612, 'Medium Orchid3', 0xB452CDFF),
        (613, 'Medium Orchid4', 0x7A378BFF),
        (614, 'Medium Purple', 0x9370DBFF),
        (615, 'Medium Purple1', 0xAB82FFFF),
        (616, 'Medium Purple2', 0x9F79EEFF),
        (617, 'Medium Purple3', 0x8968CDFF),
        (618, 'Medium Purple4', 0x5D478BFF),
        (619, 'Medium SeaG reen', 0x3CB371FF),
        (620, 'Medium Slate Blue', 0x7B68EEFF),
        (621, 'Medium Spring Green', 0x00FA9AFF),
        (622, 'Medium Turquoise', 0x48D1CCFF),
        (623, 'Medium Violet Red', 0xC71585FF),
        (624, 'Mellow Apricot', 0xF8B878FF),
        (625, 'Melon', 0xFEBAADFF),
        (626, 'Metallic Gold', 0xD3AF37FF),
        (627, 'Metallic Seaweed', 0x0A7E8CFF),
        (628, 'Metallic Sunburst', 0x9C7C38FF),
        (629, 'Mexican Pink', 0xE4007CFF),
        (630, 'Medium Blue', 0x7ED4E6FF),
        (631, 'Medium Blue Green', 0x8DD9CCFF),
        (632, 'Medium Blue Purple', 0x8B72BEFF),
        (633, 'Medium Green', 0x4D8C57FF),
        (634, 'Medium Green Yellow', 0xACBF60FF),
        (635, 'Medium Gray', 0x8B8680FF),
        (636, 'Medium Red', 0xE58E73FF),
        (637, 'Medium Red Purple', 0xA55353FF),
        (638, 'Medium Yellow', 0xFFEB00FF),
        (639, 'Medium Yellow Red', 0xECB176FF),
        (640, 'Midnight Green', 0x004953FF),
        (641, 'Midnight Blue', 0x191970FF),
        (642, 'Mikado Yellow', 0xFFC40CFF),
        (643, 'Mimi Pink', 0xFFDAE9FF),
        (644, 'Mindaro', 0xE3F988FF),
        (645, 'Minion Yellow', 0xF5E050FF),
        (646, 'Mint', 0x3EB489FF),
        (647, 'Mint Green', 0x98FF98FF),
        (648, 'Mint Cream', 0xF5FFFAFF),
        (649, 'Misty Moss', 0xBBB477FF),
        (650, 'Misty Rose1', 0xFFE4E1FF),
        (651, 'Misty Rose2', 0xEED5D2FF),
        (652, 'Misty Rose3', 0xCDB7B5FF),
        (653, 'Misty Rose4', 0x8B7D7BFF),
        (654, 'Moccasin', 0xFFE4B5FF),
        (655, 'Mode Beige', 0x967117FF),
        (656, 'Moss Green', 0x8A9A5BFF),
        (657, 'Mountain Meadow', 0x30BA8FFF),
        (658, 'Mountbatten Pink', 0x997A8DFF),
        (659, 'Mulberry', 0xC54B8CFF),
        (660, 'Mustard', 0xFFDB58FF),
        (661, 'Myrtle Green', 0x317873FF),
        (662, 'Mystic Maroon', 0xAD4379FF),
        (663, 'Nadeshiko Pink', 0xF6ADC6FF),
        (664, 'Navajo White1', 0xFFDEADFF),
        (665, 'Navajo White2', 0xEECFA1FF),
        (666, 'Navajo White3', 0xCDB38BFF),
        (667, 'Navajo White4', 0x8B795EFF),
        (668, 'Navy Blue', 0x000080FF),
        (669, 'Neon Blue', 0x4666FFFF),
        (670, 'Neon Carrot', 0xFFA343FF),
        (671, 'Neon Fuchsia', 0xFE4164FF),
        (672, 'Neon Green', 0x39FF14FF),
        (673, 'Nickel', 0x727472FF),
        (674, 'Nyanza', 0xE9FFDBFF),
        (675, 'Ocean Blue', 0x4F42B5FF),
        (676, 'Ocean Green', 0x48BF91FF),
        (677, 'Ochre', 0xCC7722FF),
        (678, 'Old Burgundy', 0x43302EFF),
        (679, 'Old Gold', 0xCFB53BFF),
        (680, 'Old Lavender', 0x796878FF),
        (681, 'Old Mauve', 0x673147FF),
        (682, 'Old Rose', 0xC08081FF),
        (683, 'Old Lace', 0xFDF5E6FF),
        (684, 'Olive', 0x808000FF),
        (685, 'Olive Green', 0xB5B35CFF),
        (686, 'Olive Drab', 0x6B8E23FF),
        (687, 'Olive Drab1', 0xC0FF3EFF),
        (688, 'Olive Drab2', 0xB3EE3AFF),
        (689, 'Olive Drab4', 0x698B22FF),
        (690, 'Olivine', 0x9AB973FF),
        (691, 'Opal', 0xA8C3BCFF),
        (692, 'Opera Maue', 0xB784A7FF),
        (693, 'Orange (Crayola)', 0xFF5800FF),
        (694, 'Orange Peel', 0xFF9F00FF),
        (695, 'Orange Soda', 0xFA5B3DFF),
        (696, 'Orange1', 0xFFA500FF),
        (697, 'Orange2', 0xEE9A00FF),
        (698, 'Orange3', 0xCD8500FF),
        (699, 'Orange4', 0x8B5A00FF),
        (700, 'Orange Red1', 0xFF4500FF),
        (701, 'Orange Red2', 0xEE4000FF),
        (702, 'Orange Red3', 0xCD3700FF),
        (703, 'Orange Red4', 0x8B2500FF),
        (704, 'Orchid', 0xDA70D6FF),
        (705, 'Orchid (Crayola)', 0xE29CD2FF),
        (706, 'Orchid Pink', 0xF2BDCDFF),
        (707, 'Orchid1', 0xFF83FAFF),
        (708, 'Orchid2', 0xEE7AE9FF),
        (709, 'Orchid3', 0xCD69C9FF),
        (710, 'Orchid4', 0x8B4789FF),
        (711, 'Outrageous Orange', 0xFF6E4AFF),
        (712, 'Oxblood', 0x4A0000FF),
        (713, 'Oxford Blue', 0x002147FF),
        (714, 'Pacific Blue', 0x1CA9C9FF),
        (715, 'Palatinate Purple', 0x682860FF),
        (716, 'Pale', 0xDB7093FF),
        (717, 'Pale Aqua', 0xBCD4E6FF),
        (718, 'Pale Cerulean', 0x9BC4E2FF),
        (719, 'Pale Pink', 0xFADADDFF),
        (720, 'Pale Silver', 0xC9C0BBFF),
        (721, 'Pale Spring Bud', 0xECEBBDFF),
        (722, 'Pale Goldenrod', 0xEEE8AAFF),
        (723, 'Pale Green', 0x98FB98FF),
        (724, 'Pale Green1', 0x9AFF9AFF),
        (725, 'Light Green', 0x90EE90FF),
        (726, 'Pale Green3', 0x7CCD7CFF),
        (727, 'Pale Green4', 0x548B54FF),
        (728, 'Pale Turquoise', 0xAFEEEEFF),
        (729, 'Pale Turquoise1', 0xBBFFFFFF),
        (730, 'Pale Turquoise2', 0xAEEEEEFF),
        (731, 'Pale Turquoise3', 0x96CDCDFF),
        (732, 'Pale Turquoise4', 0x668B8BFF),
        (733, 'Pale Violet Red', 0xDB7093FF),
        (734, 'Pale Violet Red1', 0xFF82ABFF),
        (735, 'Pale Violet Red2', 0xEE799FFF),
        (736, 'Pale Violet Red3', 0xCD6889FF),
        (737, 'Pale Violet Red4', 0x8B475DFF),
        (738, 'Pansy Purple', 0x78184AFF),
        (739, 'Papaya Whip', 0xFFEFD5FF),
        (740, 'Paradise Pink', 0xE63E62FF),
        (741, 'Pastel Pink', 0xDEA5A4FF),
        (742, 'Patriarch (Purple)', 0x800080FF),
        (743, 'Peach', 0xFFE5B4FF),
        (744, 'Peach Puff1', 0xFFDAB9FF),
        (745, 'Peach Puff2', 0xEECBADFF),
        (746, 'Peach Puff3', 0xCDAF95FF),
        (747, 'Peach Puff4', 0x8B7765FF),
        (748, 'Pear', 0xD1E231FF),
        (749, 'Pearly Purple', 0xB768A2FF),
        (750, 'Persian Blue', 0x1C39BBFF),
        (751, 'Persian Green', 0x00A693FF),
        (752, 'Persian Indigo', 0x32127AFF),
        (753, 'Persian Orange', 0xD99058FF),
        (754, 'Persian Pink', 0xF77FBEFF),
        (755, 'Persian Plum', 0x701C1CFF),
        (756, 'Persian Red', 0xCC3333FF),
        (757, 'Persian Rose', 0xFE28A2FF),
        (758, 'Pewter Blue', 0x8BA8B7FF),
        (759, 'Phthalo Blue', 0x000F89FF),
        (760, 'Phthalo Green', 0x123524FF),
        (761, 'Pictorial Carmine', 0xC30B4EFF),
        (762, 'Piggy Pink', 0xFDDDE6FF),
        (763, 'Pine Green', 0x01796FFF),
        (764, 'Pine Tree', 0x2A2F23FF),
        (765, 'Pink', 0xFFC0CBFF),
        (766, 'Pink (Pantone)', 0xD74894FF),
        (767, 'Pink Flamingo', 0xFC74FDFF),
        (768, 'Pink Sherbet', 0xF78FA7FF),
        (769, 'Pink1', 0xFFB5C5FF),
        (770, 'Pink2', 0xEEA9B8FF),
        (771, 'Pink3', 0xCD919EFF),
        (772, 'Pink4', 0x8B636CFF),
        (773, 'Pistachio', 0x93C572FF),
        (774, 'Platinum', 0xE5E4E2FF),
        (775, 'Plum', 0x8E4585FF),
        (776, 'Plum1', 0xFFBBFFFF),
        (777, 'Plum2', 0xEEAEEEFF),
        (778, 'Plum3', 0xCD96CDFF),
        (779, 'Plum4', 0x8B668BFF),
        (780, 'Plump Purple', 0x5946B2FF),
        (781, 'Portland Orange', 0xFF5A36FF),
        (782, 'Powder Blue', 0xB0E0E6FF),
        (783, 'Prussian Blue', 0x003153FF),
        (784, 'Puce', 0xCC8899FF),
        (785, 'Pumpkin', 0xFF7518FF),
        (786, 'Purple', 0xA020F0FF),
        (787, 'Purple1', 0x9B30FFFF),
        (788, 'Purple2', 0x912CEEFF),
        (789, 'Purple3', 0x7D26CDFF),
        (790, 'Purple4', 0x551A8BFF),
        (791, 'Quinacridone Magenta', 0x8E3A59FF),
        (792, 'Radical Red', 0xFF355EFF),
        (793, 'Raspberry', 0xE30B5DFF),
        (794, 'Razzmatazz', 0xE3256BFF),
        (795, 'Rebeccapurple', 0x663399FF),
        (796, 'Red Orange', 0xFF5349FF),
        (797, 'Bright Red', 0xFF0000FF),
        (798, 'Red2', 0xEE0000FF),
        (799, 'Red3', 0xCD0000FF),
        (800, 'Dark Red', 0x950606FF),
        (801, 'Redwood', 0xA45A52FF),
        (802, 'Rifle Green', 0x444C38FF),
        (803, 'Rocket Metallic', 0x8A7F80FF),
        (804, 'Rose', 0xFF007FFF),
        (805, 'Rose Bonbon', 0xF9429EFF),
        (806, 'Rose Dust', 0x9E5E6FFF),
        (807, 'Rose Pink', 0xFF66CCFF),
        (808, 'Rose Taupe', 0x905D5DFF),
        (809, 'Rosewood', 0x65000BFF),
        (810, 'Rosy Brown', 0xBC8F8FFF),
        (811, 'Rosy Brown1', 0xFFC1C1FF),
        (812, 'Rosy Brown2', 0xEEB4B4FF),
        (813, 'Rosy Brown3', 0xCD9B9BFF),
        (814, 'Rosy Brown4', 0x8B6969FF),
        (815, 'Royal Blue', 0x4169E1FF),
        (816, 'Royal Blue1', 0x4876FFFF),
        (817, 'Royal Blue2', 0x436EEEFF),
        (818, 'Royal Blue3', 0x3A5FCDFF),
        (819, 'Royal Blue4', 0x27408BFF),
        (820, 'Ruby', 0xE0115FFF),
        (821, 'Russet', 0x80461BFF),
        (822, 'Russian Green', 0x679267FF),
        (823, 'Russian Violet', 0x32174DFF),
        (824, 'Rust', 0xB7410EFF),
        (825, 'Saddle Brown', 0x8B4513FF),
        (826, 'Saffron', 0xF4C430FF),
        (827, 'Sage', 0xBCB88AFF),
        (828, 'Salmon', 0xFA8072FF),
        (829, 'Salmon1', 0xFF8C69FF),
        (830, 'Salmon2', 0xEE8262FF),
        (831, 'Salmon3', 0xCD7054FF),
        (832, 'Salmon4', 0x8B4C39FF),
        (833, 'Sandy Brown', 0xF4A460FF),
        (834, 'Sap Green', 0x507D2AFF),
        (835, 'Sapphire', 0x0F52BAFF),
        (836, 'Scarlet', 0xFF2400FF),
        (837, 'School Bus Yellow', 0xFFD800FF),
        (838, 'Sea Green1', 0x54FF9FFF),
        (839, 'Sea Green2', 0x4EEE94FF),
        (840, 'Sea Green3', 0x43CD80FF),
        (841, 'Sea Green4', 0x2E8B57FF),
        (842, 'Seal Brown', 0x59260BFF),
        (843, 'Seashell1', 0xFFF5EEFF),
        (844, 'Seashell2', 0xEEE5DEFF),
        (845, 'Seashell3', 0xCDC5BFFF),
        (846, 'Seashell4', 0x8B8682FF),
        (847, 'Selective Yellow', 0xFFBA00FF),
        (848, 'Sepia', 0x704214FF),
        (849, 'Shamrock Green', 0x009E60FF),
        (850, 'Shocking Pink', 0xFC0FC0FF),
        (851, 'Sienna', 0xA0522DFF),
        (852, 'Sienna1', 0xFF8247FF),
        (853, 'Sienna2', 0xEE7942FF),
        (854, 'Sienna3', 0xCD6839FF),
        (855, 'Sienna4', 0x8B4726FF),
        (856, 'Stainless Steel', 0xC0C0C0FF),
        (857, 'Silver Pink', 0xC4AEADFF),
        (858, 'Sinopia', 0xCB410BFF),
        (859, 'Skobeloff', 0x007474FF),
        (860, 'Sky Blue', 0x87CEEBFF),
        (861, 'Sky Blue1', 0x87CEFFFF),
        (862, 'Sky Blue2', 0x7EC0EEFF),
        (863, 'Sky Blue3', 0x6CA6CDFF),
        (864, 'Sky Blue4', 0x4A708BFF),
        (865, 'Slate Blue', 0x6A5ACDFF),
        (866, 'Slate Blue1', 0x836FFFFF),
        (867, 'Slate Blue2', 0x7A67EEFF),
        (868, 'Slate Blue3', 0x6959CDFF),
        (869, 'Slate Blue4', 0x473C8BFF),
        (870, 'Slate Gray', 0x708090FF),
        (871, 'Slate Gray1', 0xC6E2FFFF),
        (872, 'Slate Gray2', 0xB9D3EEFF),
        (873, 'Slate Gray3', 0x9FB6CDFF),
        (874, 'Slate Gray4', 0x6C7B8BFF),
        (875, 'Smoky Black', 0x100C08FF),
        (876, 'Snow1', 0xFFFAFAFF),
        (877, 'Snow2', 0xEEE9E9FF),
        (878, 'Snow3', 0xCDC9C9FF),
        (879, 'Snow4', 0x8B8989FF),
        (880, 'Spanish Bistre', 0x807532FF),
        (881, 'Spanish Orange', 0xE86100FF),
        (882, 'Spanish Pink', 0xF7BFBEFF),
        (883, 'Spanish Viridian', 0x007F5CFF),
        (884, 'Spring Bud', 0xA7FC00FF),
        (885, 'Spring Frost', 0x87FF2AFF),
        (886, 'Spring Green1', 0x00FF7FFF),
        (887, 'Spring Green2', 0x00EE76FF),
        (888, 'Spring Green3', 0x00CD66FF),
        (889, 'Spring Green4', 0x008B45FF),
        (890, 'Steel Pink', 0xCC33CCFF),
        (891, 'Steel Blue', 0x4682B4FF),
        (892, 'Steel Blue1', 0x63B8FFFF),
        (893, 'Steel Blue2', 0x5CACEEFF),
        (894, 'Steel Blue3', 0x4F94CDFF),
        (895, 'Steel Blue4', 0x36648BFF),
        (896, 'Straw', 0xE4D96FFF),
        (897, 'Sunglow', 0xFFCC33FF),
        (898, 'Super Pink', 0xCF6BA9FF),
        (899, 'Sweet Brown', 0xA83731FF),
        (900, 'Tan', 0xD2B48CFF),
        (901, 'Tan1', 0xFFA54FFF),
        (902, 'Tan2', 0xEE9A49FF),
        (903, 'Tan3', 0xCD853FFF),
        (904, 'Tan4', 0x8B5A2BFF),
        (905, 'Tangerine', 0xF28500FF),
        (906, 'Tart Orange', 0xFB4D46FF),
        (907, 'Taupe', 0x483C32FF),
        (908, 'Taupe Gray', 0x8B8589FF),
        (909, 'Tea Green', 0xD0F0C0FF),
        (910, 'Teal', 0x008080FF),
        (911, 'Teal Blue', 0x367588FF),
        (912, 'Terra Cotta', 0xE2725BFF),
        (913, 'Thistle', 0xD8BFD8FF),
        (914, 'Thistle1', 0xFFE1FFFF),
        (915, 'Thistle2', 0xEED2EEFF),
        (916, 'Thistle3', 0xCDB5CDFF),
        (917, 'Thistle4', 0x8B7B8BFF),
        (918, 'Tiffany Blue', 0x0ABAB5FF),
        (919, 'Timberwolf', 0xDBD7D2FF),
        (920, 'Titanium Yellow', 0xEEE600FF),
        (921, 'Tomato1', 0xFF6347FF),
        (922, 'Tomato2', 0xEE5C42FF),
        (923, 'Tomato3', 0xCD4F39FF),
        (924, 'Tomato4', 0x8B3626FF),
        (925, 'Tropical Rainforest', 0x00755EFF),
        (926, 'Tumbleweed', 0xDEAA88FF),
        (927, 'Turquoise', 0x40E0D0FF),
        (928, 'Turquoise Blue', 0x00FFEFFF),
        (929, 'Turquoise1', 0x00F5FFFF),
        (930, 'Turquoise2', 0x00E5EEFF),
        (931, 'Turquoise3', 0x00C5CDFF),
        (932, 'Turquoise4', 0x00868BFF),
        (933, 'Tuscan Red', 0x7C4848FF),
        (934, 'Tuscany', 0xC09999FF),
        (935, 'Twilight Lavender', 0x8A496BFF),
        (936, 'Tyrian Purple', 0x66023CFF),
        (937, 'UP Forest Green', 0x014421FF),
        (938, 'UP Maroon', 0x7B1113FF),
        (939, 'Ultra Pink', 0xFF6FFFFF),
        (940, 'Ultramarine', 0x3F00FFFF),
        (941, 'Ultramarine Blue', 0x4166F5FF),
        (942, 'Unbleached Silk', 0xFFDDCAFF),
        (943, 'United Nations Blue', 0x5B92E5FF),
        (944, 'Upsdell Red', 0xAE2029FF),
        (945, 'Van Dyke Brown', 0x664228FF),
        (946, 'Vanilla', 0xF3E5ABFF),
        (947, 'Vanilla Ice', 0xF38FA9FF),
        (948, 'Vegas Gold', 0xC5B358FF),
        (949, 'Venetian Red', 0xC80815FF),
        (950, 'Verdigris', 0x43B3AEFF),
        (951, 'Vermillion', 0xE34234FF),
        (952, 'Violet Red', 0xD02090FF),
        (953, 'Violet Red1', 0xFF3E96FF),
        (954, 'Violet Red2', 0xEE3A8CFF),
        (955, 'Violet Red3', 0xCD3278FF),
        (956, 'Violet Red4', 0x8B2252FF),
        (957, 'Viridian', 0x40826DFF),
        (958, 'Viridian Green', 0x009698FF),
        (959, 'Vivid Burgundy', 0x9F1D35FF),
        (960, 'Vivid Sky Blue', 0x00CCFFFF),
        (961, 'Vivid Tangerine', 0xFFA089FF),
        (962, 'Vivid Violet', 0x9F00FFFF),
        (963, 'Volt', 0xCEFF00FF),
        (964, 'Warm Black', 0x004242FF),
        (965, 'Wheat', 0xF5DEB3FF),
        (966, 'Wheat1', 0xFFE7BAFF),
        (967, 'Wheat2', 0xEED8AEFF),
        (968, 'Wheat3', 0xCDBA96FF),
        (969, 'Wheat4', 0x8B7E66FF),
        (970, 'White Smoke', 0xF5F5F5FF),
        (971, 'Wild Blue Yonder', 0xA2ADD0FF),
        (972, 'Wild Orchid', 0xD470A2FF),
        (973, 'Wild Strawberry', 0xFF43A4FF),
        (974, 'Windsor Tan', 0xA75502FF),
        (975, 'Wine', 0x722F37FF),
        (976, 'Wintergreen Dream', 0x56887DFF),
        (977, 'Wisteria', 0xC9A0DCFF),
        (978, 'Xanadu', 0x738678FF),
        (979, 'Yellow Orange', 0xFFAE42FF),
        (980, 'Yellow Pantone', 0xFEDF00FF),
        (981, 'Yellow1', 0xFFFF00FF),
        (982, 'Yellow2', 0xEEEE00FF),
        (983, 'Yellow3', 0xCDCD00FF),
        (984, 'Yellow4', 0x8B8B00FF),
        (985, 'Yellow Green', 0x9ACD32FF),
        (986, 'Zaffre', 0x0014A8FF),
        (987, 'Zomp', 0x39A78EFF),
        (988, 'Blue Gray', 0x6699CCFF),
        (989, 'Nut Brown', 0x583827FF),
        (990, 'Leaf Green', 0x276235FF),
        (991, 'Claret Violet', 0x0A8DB7FF),
        (992, 'Signal Blue', 0x154889FF),
        (993, 'Water Blue', 0x007577FF),
        (994, 'Natural White', 0xF9F7F8FF),
        (995, 'Pastel Green', 0xC1E1C1FF),
        (996, 'Curry', 0x874010FF),
        (997, 'Platinum Gray', 0xA8A9A3FF),
        (998, 'Pure White', 0xFFFFFFFF),
        (999, 'Heather Violet', 0xC4608CFF),
        (1000, 'Natural', 0xE5D3BFFF),
        (1001, 'Light Brown', 0xC4A484FF),
        (1002, 'Cream White', 0xFCFBF4FF),
        (1003, 'Light Purple', 0xCBC3E3FF),
        (1004, 'Curry Yellow', 0xE9DA89FF),
        (1005, 'Carmine Red', 0xFF0038FF),
        (1006, 'Pastel Orange', 0xFAC898FF),
        (1007, 'Grafe Violet', 0x4C2882FF),
        (1008, 'Gabriel', 0x4B3C8EFF),
        (1009, 'Brown Red', 0x7B3F00FF),
        (1010, 'Metal', 0xA9A9A9FF),
        (1011, 'Light Red', 0xFF4D4DFF),
        (1012, 'Cadillac Gray', 0xB2B1B0FF),
        (1013, 'Dark Purple', 0x301934FF),
        (1014, 'Silver', 0xC0C0C0FF),
        (1015, 'Red Brown', 0x942222FF),
        (1016, 'Aluminum', 0xC6C7C7),
        (1017, 'Titanium', 0x878681),
        (1018, 'Zinc', 0xBAC4C8),
        (1019, 'Multiple Colors', 0x000000FF),
        (1020, 'Transparent', 0xFFFFFF00),
        (999999, 'None', 0x00000000)
    )


def _build_temps():
    data = [(0, 'Unknown',)]

    for i in range(-100, 305, 5):
        if i > 0:
            i = '+' + str(i)
        else:
            i = str(i)

        i += '°C'
        data.append((len(data), i))

    return data


def _build_wire_markers(con, cur):
    data = {
        'SH RNF-3000-3/1-{color_id}': {
            'min_awg': 18,
            'max_awg': 10,
            'description': 'Shrink Markers ({color}/Standard)',
            'min_diameter': 1.0,
            'max_diameter': 3.0,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20RNF-3000-3%201-{color_id}_thumbnail.jpg'
        },
        'SH RNF-3000-0-{color_id}': {
            'min_awg': 26,
            'max_awg': 18,
            'description': 'Shrink Markers ({color}/Mini)',
            'min_diameter': 0.5,
            'max_diameter': 1.5,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20RNF-3000-{color_id}_thumbnail.jpg'
        }
    }

    color_mapping = {
        0: 'Black',
        1: 'Brown',
        2: 'Red',
        3: 'Orange',
        4: 'Yellow',
        5: 'Green',
        6: 'Blue',
        7: 'Violet',
        8: 'Gray',
        9: 'White'
    }

    mfg_id = get_mfg_id(con, cur, 'Milspecwiring.com')
    res = []

    for color_id, color_name in color_mapping.items():
        for pn, item_data in data.items():
            part_number = pn.format(color_id=color_id)
            description = item_data['description'].format(color=color_name)
            min_awg = item_data['min_awg']
            max_awg = item_data['max_awg']
            min_diameter = item_data['min_diameter']
            max_diameter = item_data['max_diameter']
            image_url = item_data['image_url'].format(color_id=color_id)
            length = 5.0
            weight = 0.0
            datasheet_id = 0
            cad_id = 0
            has_label = 0

            image_id = get_resource_id(con, cur, image_url, type='jpg')

            res.append((part_number, description, mfg_id, color_id, min_diameter,
                        max_diameter, min_awg, max_awg, image_id, datasheet_id, cad_id,
                        length, weight, has_label))

    data = {
        'SH CT 3/32K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/32" Shrink Label',
            'min_diameter': 0.79,
            'max_diameter': 2.36,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/8K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/8" Shrink Label',
            'min_diameter': 1.07,
            'max_diameter': 3.18,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 3/16K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/16" Shrink Label',
            'min_diameter': 1.57,
            'max_diameter': 4.75,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/4K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/4" Shrink Label',
            'min_diameter': 6.35,
            'max_diameter': 2.11,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 3/8K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/8" Shrink Label',
            'min_diameter': 3.18,
            'max_diameter': 9.53,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/2" Shrink Label',
            'min_diameter': 4.22,
            'max_diameter': 12.7,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20half%20inch_thumbnail.jpg'

        },
        'SH CT 3/4K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/4" Shrink Label',
            'min_diameter': 6.35,
            'max_diameter': 19.05,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20half%20inch_thumbnail.jpg'

        },
        'SH CT 1K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1" Shrink Label',
            'min_diameter': 8.46,
            'max_diameter': 25.4,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        },
        'SH CT 1-1/2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1-1/2" Shrink Label',
            'min_diameter': 19.05,
            'max_diameter': 38.1,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        },
        'SH CT 2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 2" Shrink Label',
            'min_diameter': 25.4,
            'max_diameter': 50.8,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        }
    }

    for part_number, item_data in data.items():

        description = item_data['description']
        min_awg = item_data['min_awg']
        max_awg = item_data['max_awg']
        has_label = 1
        min_diameter = item_data['min_diameter']
        max_diameter = item_data['max_diameter']
        image_url = item_data['image_url']
        length = -1.0
        weight = 0.0
        datasheet_id = 0
        cad_id = 0

        image_id = get_resource_id(con, cur, image_url, type='jpg')

        res.append((part_number, description, mfg_id, 1020, min_diameter,
                    max_diameter, min_awg, max_awg, image_id, datasheet_id, cad_id,
                    length, weight, has_label))
    print(res)

    return res


def _build_wires(con, cur):
    mapping = {
        'M22759/5': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 6.48,
                    'weight': 115.0,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 4.73,
                    'weight': 63.3,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 4.24,
                    'weight': 46.0,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 3.81,
                    'weight': 33.5,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 3.30,
                    'weight': 24.7,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.92,
                    'weight': 19.2,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.54,
                    'weight': 13.6,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 2.29,
                    'weight': 10.1,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 2.03,
                    'weight': 7.60,
                    'resistance': 79.7
                }

            }
        },
        'M22759/6': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.14,
                    'od': 6.48,
                    'weight': 118.0,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.77,
                    'od': 4.73,
                    'weight': 64.8,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 4.24,
                    'weight': 47.5,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 3.81,
                    'weight': 34.7,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 3.30,
                    'weight': 25.2,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 2.92,
                    'weight': 19.5,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.54,
                    'weight': 13.9,
                    'resistance': 32.1
                },
                22: {
                    'dia': 0.76,
                    'od': 2.29,
                    'weight': 10.4,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 2.03,
                    'weight': 7.70,
                    'resistance': 85.0
                }

            }
        },
        'M22759/7': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.72,
                    'weight': 101.0,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 4.11,
                    'weight': 55.7,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 3.48,
                    'weight': 38.3,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 3.00,
                    'weight': 25.8,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.67,
                    'weight': 18.9,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.39,
                    'weight': 15.2,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.13,
                    'weight': 10.9,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.91,
                    'weight': 7.44,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.63,
                    'weight': 5.51,
                    'resistance': 79.7
                }

            }
        },
        'M22759/8': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.14,
                    'od': 5.72,
                    'weight': 104.0,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.77,
                    'od': 4.11,
                    'weight': 57.2,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 3.48,
                    'weight': 42.8,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 3.00,
                    'weight': 27.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.67,
                    'weight': 19.4,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 2.39,
                    'weight': 15.5,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.13,
                    'weight': 11.2,
                    'resistance': 32.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.91,
                    'weight': 7.66,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.63,
                    'weight': 5.66,
                    'resistance': 85.0
                }

            }
        },
        'M22759/9': {
            'start': 8,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.38,
                    'weight': 97.3,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 3.68,
                    'weight': 52.5,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 3.15,
                    'weight': 34.7,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 2.62,
                    'weight': 24.0,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.21,
                    'weight': 15.8,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.03,
                    'weight': 12.9,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 209.0
                }
            }
        },
        'M22759/10': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.13,
                    'weight': 98.8,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.74,
                    'od': 3.48,
                    'weight': 53.4,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 2.95,
                    'weight': 34.8,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 2.46,
                    'weight': 24.1,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.11,
                    'weight': 16.1,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.93,
                    'weight': 12.9,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.68,
                    'weight': 9.06,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.47,
                    'weight': 6.40,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.30,
                    'weight': 4.66,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.17,
                    'weight': 3.54,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 223.0
                }
            }
        },
        'M22759/11': {
            'start': 8,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.23,
                    'weight': 86.1,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 3.63,
                    'weight': 52.0,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 2.90,
                    'weight': 35.0,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 2.34,
                    'weight': 21.9,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 1.96,
                    'weight': 14.3,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.78,
                    'weight': 11.3,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.66,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.12,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.59,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.59,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.82,
                    'resistance': 209.0
                }
            }
        },
        'M22759/12': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.28,
                    'weight': 87.5,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.74,
                    'od': 3.63,
                    'weight': 52.8,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 2.90,
                    'weight': 35.7,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 2.34,
                    'weight': 22.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 1.96,
                    'weight': 14.5,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.78,
                    'weight': 11.4,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.72,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.15,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.60,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.60,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.83,
                    'resistance': 223.0
                }
            }
        },
        'M22759/16': {
            'start': -2,
            'stop': 25,
            'step': 1,
            'con_plate': 'Sn/Cu',
            'material': 'Extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                -2: {
                    'dia': 11.7,
                    'od': 14.0,
                    'weight': 722.0,
                    'resistance': 0.299
                },
                -1: {
                    'dia': 10.5,
                    'od': 12.3,
                    'weight': 566.0,
                    'resistance': 0.380
                },
                1: {
                    'dia': 9.40,
                    'od': 11.1,
                    'weight': 437.0,
                    'resistance': 0.489
                },
                2: {
                    'dia': 8.38,
                    'od': 9.96,
                    'weight': 344.0,
                    'resistance': 0.600
                },
                4: {
                    'dia': 6.60,
                    'od': 8.03,
                    'weight': 227.0,
                    'resistance': 0.916
                },
                6: {
                    'dia': 5.13,
                    'od': 6.43,
                    'weight': 144.0,
                    'resistance': 1.46
                },
                8: {
                    'dia': 4.11,
                    'od': 5.13,
                    'weight': 91.5,
                    'resistance': 2.30
                },
                10: {
                    'dia': 2.79,
                    'od': 3.61,
                    'weight': 50.6,
                    'resistance': 4.13
                },
                12: {
                    'dia': 2.18,
                    'od': 2.97,
                    'weight': 32.4,
                    'resistance': 6.63
                },
                14: {
                    'dia': 1.70,
                    'od': 2.41,
                    'weight': 21.6,
                    'resistance': 10.0
                },
                16: {
                    'dia': 1.35,
                    'od': 2.06,
                    'weight': 14.4,
                    'resistance': 15.8
                },
                18: {
                    'dia': 1.22,
                    'od': 1.85,
                    'weight': 11.4,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.97,
                    'od': 1.57,
                    'weight': 7.71,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.37,
                    'weight': 5.24,
                    'resistance': 53.1
                },
                24: {
                    'dia': 0.61,
                    'od': 1.19,
                    'weight': 3.65,
                    'resistance': 85.9
                }
            }
        },
        'M22759/17': {
            'start': 20,
            'stop': 27,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.57,
                    'weight': 7.38,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.37,
                    'weight': 5.06,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.19,
                    'weight': 3.45,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.07,
                    'weight': 2.49,
                    'resistance': 147.0
                }
            }
        },
        'M22759/18': {
            'start': 10,
            'stop': 27,
            'step': 2,
            'con_plate': 'Sn/Cu',
            'material': 'Thin-wall extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                10: {
                    'dia': 2.79,
                    'od': 3.48,
                    'weight': 49.3,
                    'resistance': 4.13
                },
                12: {
                    'dia': 2.18,
                    'od': 2.80,
                    'weight': 31.3,
                    'resistance': 6.63
                },
                14: {
                    'dia': 1.70,
                    'od': 2.21,
                    'weight': 20.4,
                    'resistance': 10.0
                },
                16: {
                    'dia': 1.35,
                    'od': 1.83,
                    'weight': 13.3,
                    'resistance': 15.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.60,
                    'weight': 10.3,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.97,
                    'od': 1.35,
                    'weight': 6.85,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.14,
                    'weight': 4.52,
                    'resistance': 53.1
                },
                24: {
                    'dia': 0.61,
                    'od': 0.97,
                    'weight': 3.01,
                    'resistance': 85.9
                },
                26: {
                    'dia': 0.48,
                    'od': 0.86,
                    'weight': 2.26,
                    'resistance': 135.0
                }
            }
        },
        'M22759/19': {
            'start': 20,
            'stop': 27,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Thin-wall extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.35,
                    'weight': 6.62,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.14,
                    'weight': 4.27,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 0.97,
                    'weight': 2.86,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 0.86,
                    'weight': 2.02,
                    'resistance': 147.0
                }
            }
        },
        'M22759/20': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 244.0
                }
            }
        },
        'M22759/21': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 259.0
                }
            }
        },
        'M22759/22': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Thin-wall extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.72,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.28,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.74,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.74,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.89,
                    'resistance': 244.0
                }
            }
        },
        'M22759/23': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Thin-wall extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.84,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.39,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.79,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.77,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.92,
                    'resistance': 259.0
                }
            }
        },
        'M22759/28': {
            'start': 14,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                14: {
                    'dia': 1.70,
                    'od': 2.39,
                    'weight': 22.0,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.01,
                    'weight': 14.5,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.80,
                    'weight': 11.4,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 209.0
                }
            }
        },
        'M22759/29': {
            'start': 14,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                14: {
                    'dia': 1.70,
                    'od': 2.39,
                    'weight': 22.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.01,
                    'weight': 14.5,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.80,
                    'weight': 11.4,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 223.0
                }
            }
        },
        'M22759/30': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 244.0
                }
            }
        },
        'M22759/31': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.86,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.24,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.69,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.69,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.90,
                    'resistance': 259.0
                }
            }
        },
        'M22759/32': {
            'start': 12,
            'stop': 31,
            'step': 2,
            'con_plate': 'Sn/Cu',
            'material': 'Fluoropolymer Cross-linked Modified (ETFE)',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                12: {
                    'dia': 0.0,
                    'od': 2.62,
                    'weight': 29.0,
                    'resistance': 6.63
                },
                14: {
                    'dia': 0.0,
                    'od': 2.16,
                    'weight': 19.0,
                    'resistance': 10.0
                },
                16: {
                    'dia': 0.0,
                    'od': 1.73,
                    'weight': 12.3,
                    'resistance': 15.8
                },
                18: {
                    'dia': 0.0,
                    'od': 1.52,
                    'weight': 9.67,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.0,
                    'od': 1.27,
                    'weight': 6.40,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.0,
                    'od': 1.09,
                    'weight': 4.17,
                    'resistance': 53.2
                },
                24: {
                    'dia': 0.0,
                    'od': 0.94,
                    'weight': 2.98,
                    'resistance': 86.0
                },
                26: {
                    'dia': 0.0,
                    'od': 0.81,
                    'weight': 2.08,
                    'resistance': 136.0
                },
                28: {
                    'dia': 0.0,
                    'od': 0.68,
                    'weight': 1.35,
                    'resistance': 225.0
                },
                30: {
                    'dia': 0.0,
                    'od': 0.61,
                    'weight': 0.98,
                    'resistance': 330.0
                }
            }
        },
        # 'M22759/80': {},
        # 'M22759/81': {},
        # 'M22759/82': {},
        # 'M22759/83': {},
        # 'M22759/84': {},
        # 'M22759/85': {},
        # 'M22759/86': {},
        # 'M22759/87': {},
        # 'M22759/88': {},
        # 'M22759/89': {},
        # 'M22759/90': {},
        # 'M22759/91': {},
        # 'M22759/92': {}
    }

    color_mapping = {
        0: 'Black',
        1: 'Brown',
        2: 'Red',
        3: 'Orange',
        4: 'Yellow',
        5: 'Green',
        6: 'Blue',
        7: 'Violet',
        8: 'Gray',
        9: 'White'
    }

    def __awg_to_mm2(a: int) -> float:
        d_in = 0.005 * (92 ** ((36 - a) / 39))
        d_mm = d_in * 25.4
        area_mm2 = (math.pi / 4) * (d_mm ** 2)
        return round(area_mm2, 4)

    pn_template = '{series}-{awg}-{primary}{secondary}'

    values = []
    mfg_id = get_mfg_id(con, cur, 'TE')

    family_id = get_family_id(con, cur, 'Tefzel', mfg_id)

    for series, wire_data in mapping.items():
        series_id = get_series_id(con, cur, series, 2)
        plating_id = get_plating_id(con, cur, wire_data['con_plate'])
        min_temp = str(wire_data['min_temp']) + '°C'
        max_temp = '+' + str(wire_data['max_temp']) + '°C'
        min_temp_id = get_temperature_id(con, cur, min_temp)
        max_temp_id = get_temperature_id(con, cur, max_temp)
        volts = wire_data['volts']
        material_id = get_material_id(con, cur, wire_data['material'])

        for awg in range(wire_data['start'], wire_data['stop'], wire_data['step']):
            if awg not in wire_data['data']:
                continue

            dia = wire_data['data'][awg]['dia']
            od_mm = wire_data['data'][awg]['od']
            weight = wire_data['data'][awg]['weight'] * 1000.0
            resistance = wire_data['data'][awg]['resistance']

            mm_2 = __awg_to_mm2(awg)

            for p_id in range(10):
                part_number = pn_template.format(series=series, awg=awg, primary=p_id, secondary='')
                description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]} Tefzel milspec single conductor wire'

                values.append((part_number, mfg_id, description, str(mm_2), awg, od_mm, dia, weight, resistance, plating_id, min_temp_id, max_temp_id, volts, material_id, p_id, 999999, family_id, series_id))
                for s_id in range(10):
                    if p_id == s_id:
                        continue
                    description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]}/{color_mapping[s_id]} Tefzel milspec single conductor wire'

                    values.append((part_number + str(s_id), mfg_id, description, mm_2, awg, od_mm, dia, weight, resistance, plating_id, min_temp_id, max_temp_id, volts, material_id, p_id, s_id, family_id, series_id))

    return values


def get_mfg_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM manufacturers WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO manufacturers (name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?);', (name, '', '', '', ''))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_temperature_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM temperatures WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO temperatures (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_gender_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM genders WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO genders (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_transition_series_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM transition_series WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO transition_series (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_protection_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM protections WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO protections (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_adhesive_id(con, cur, code):
    if not code:
        return 0

    res = cur.execute(f'SELECT id FROM adhesives WHERE code="{code}";').fetchall()

    if not res:
        cur.execute('INSERT INTO adhesives (code) VALUES (?);', (code,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_cavity_lock_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM cavity_locks WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO cavity_locks (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_color_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM colors WHERE name="{name}";').fetchall()

    if not res:
        raise RuntimeError(repr(name))
    else:
        return res[0][0]


def get_direction_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM directions WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO directions (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


# TODO: IP Rating getter


def get_plating_id(con, cur, symbol):
    if not symbol:
        return 0

    res = cur.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";').fetchall()

    if not res:
        cur.execute('INSERT INTO platings (symbol) VALUES (?);', (symbol,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_material_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM materials WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO materials (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_shape_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM shapes WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO shapes (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_series_id(con, cur, name, mfg_id):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM series WHERE name="{name}" AND mfg_id={mfg_id};').fetchall()

    if not res:
        cur.execute('INSERT INTO series (name, mfg_id) VALUES (?, ?);', (name, mfg_id))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_seal_type_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM seal_types WHERE name="{name}";').fetchall()

    if not res:
        cur.execute('INSERT INTO seal_types (name) VALUES (?);', (name,))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_family_id(con, cur, name, mfg_id):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM families WHERE name="{name}" AND mfg_id={mfg_id};').fetchall()

    if not res:
        cur.execute('INSERT INTO families (name, mfg_id) VALUES (?, ?);', (name, mfg_id))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def get_resource_id(con, cur, path, type="UNKNOWN"):
    if not path:
        return 0

    res = cur.execute(f'SELECT id FROM resources WHERE path="{path}";').fetchall()

    if not res:
        if type == 'UNKNOWN':
            if '.jpg' in path:
                type = 'jpg'
            elif '.pdf' in path:
                type = 'pdf'
            elif '.tif' in path:
                type = 'tif'
            elif '.png' in path:
                type = 'png'

        cur.execute('INSERT INTO resources (path, type) VALUES (?, ?);', (path, type))

        con.commit()
        return cur.lastrowid
    else:
        return res[0][0]


def add_cover(con, cur, part_number, description, mfg, series, length, width, height, color,
              pins, direction, min_temp, max_temp, image, cad, family=''):

    mfg_id = get_mfg_id(con, cur, mfg)
    series_id = get_series_id(con, cur, series, mfg_id)
    color_id = get_color_id(con, cur, color)
    image_id = get_resource_id(con, cur, image)
    direction_id = get_direction_id(con, cur, direction)

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if family:
            description += f' {family}'

        if color:
            description += f' {color}'

        if direction:
            description += f' {direction}'

        description += ' Cover'

    cur.execute('INSERT INTO covers (part_number, description, mfg_id, series_id, color_id, '
                'image_id, direction_id, min_temp_id, max_temp_id, length, width, '
                'height, pins) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, color_id, image_id, direction_id,
                 min_temp_id, max_temp_id, length, width, height, pins))

    con.commit()


def add_cpa_lock(con, cur, part_number, description, mfg, series, family, length, width, height, color,
                 pins, terminal_size, min_temp, max_temp, image, cad):

    mfg_id = get_mfg_id(con, cur, mfg)
    series_id = get_series_id(con, cur, series, mfg_id)
    family_id = get_family_id(con, cur, family, mfg_id)
    color_id = get_color_id(con, cur, color)
    image_id = get_resource_id(con, cur, image)
    cad_id = get_resource_id(con, cur, cad)

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        description += ' CPA Lock'

    cur.execute('INSERT INTO cpa_locks (part_number, description, mfg_id, series_id, family_id, '
                'color_id, image_id, cad_id, terminal_size, min_temp_id, max_temp_id, '
                'length, width, height, pins) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, family_id, color_id, image_id,
                 cad_id, terminal_size, min_temp_id, max_temp_id, length, width,
                 height, pins))

    con.commit()


def add_tpa_lock(con, cur, part_number, description, mfg, series, family, length, width, height, color,
                 pins, terminal_size, min_temp, max_temp, image, cad):

    mfg_id = get_mfg_id(con, cur, mfg)
    series_id = get_series_id(con, cur, series, mfg_id)
    family_id = get_family_id(con, cur, family, mfg_id)
    color_id = get_color_id(con, cur, color)
    image_id = get_resource_id(con, cur, image)
    cad_id = get_resource_id(con, cur, cad)

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        description += ' TPA Lock'

    cur.execute('INSERT INTO tpa_locks (part_number, description, mfg_id, series_id, family_id, '
                'color_id, image_id, cad_id, terminal_size, min_temp_id, max_temp_id, '
                'length, width, height, pins) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, family_id, color_id, image_id,
                 cad_id, terminal_size, min_temp_id, max_temp_id, length, width,
                 height, pins))

    con.commit()


def add_seal(con, cur, part_number, description, mfg, series, type, length, o_dia, i_dia, color,
             hardness, lubricant, min_temp, max_temp, image, cad, wire_dia_min, wire_dia_max):

    mfg_id = get_mfg_id(con, cur, mfg)
    series_id = get_series_id(con, cur, series, mfg_id)
    color_id = get_color_id(con, cur, color)
    image_id = get_resource_id(con, cur, image)
    cad_id = get_resource_id(con, cur, cad)

    type_id = get_seal_type_id(con, cur, type)

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        if wire_dia_min:
            description += f' {wire_dia_min}mm'

        if wire_dia_max:
            if wire_dia_min:
                description += f' -'

            description += f' {wire_dia_max}mm'

        if type:
            description += f' {type}'

        description += ' Seal'

    cur.execute('INSERT INTO seals (part_number, description, mfg_id, series_id, type_id, '
                'color_id, image_id, cad_id, lubricant, min_temp_id, max_temp_id, '
                'length, o_dia, i_dia, hardness, wire_dia_min, wire_dia_max) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, type_id, color_id, image_id,
                 cad_id, lubricant, min_temp_id, max_temp_id, length, o_dia,
                 i_dia, hardness, wire_dia_min, wire_dia_max))

    con.commit()


def add_terminal(con, cur, part_number, description, mfg, series, cavity_lock, wire_dia_min,
                 wire_dia_max, min_wire_cross, max_wire_cross, gender, blade_size,
                 sealing, plating, image, cad, datasheet=None):

    mfg_id = get_mfg_id(con, cur, mfg)
    series_id = get_series_id(con, cur, series, mfg_id)
    cavity_lock_id = get_cavity_lock_id(con, cur, cavity_lock)
    plating_id = get_plating_id(con, cur, plating)
    gender_id = get_gender_id(con, cur, gender)
    image_id = get_resource_id(con, cur, image)
    cad_id = get_resource_id(con, cur, cad)
    datasheet_id = get_resource_id(con, cur, datasheet)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if gender:
            description += f' {gender}'

        if blade_size:
            description += f' {blade_size}mm'

        if plating:
            description += f' {plating}'

        if min_wire_cross:
            description += f' {min_wire_cross}mm²'

        if max_wire_cross:
            if min_wire_cross:
                description += f' -'

            description += f' {max_wire_cross}mm²'

        description += ' Terminal'

    cur.execute('INSERT INTO terminals (part_number, description, mfg_id, series_id, plating_id, '
                'image_id, cad_id, gender_id, sealing, cavity_lock_id, blade_size, '
                'wire_dia_min, wire_dia_max, min_wire_cross, max_wire_cross, datasheet_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, plating_id, image_id,
                 cad_id, gender_id, sealing, cavity_lock_id, blade_size,
                 wire_dia_min, wire_dia_max, min_wire_cross, max_wire_cross, datasheet_id))

    con.commit()


def add_housing(con, cur, part_number, description, mfg, family, series, num_pins, rows,
                centerline, gender, direction, color, sealed, min_temp, max_temp,
                length, width, height, cavity_lock, terminal_sizes, mates_to,
                compat_terminals, compat_seals, compat_covers, compat_cpas,
                compat_tpas, cad, image):

    mfg_id = get_mfg_id(con, cur, mfg)
    family_id = get_family_id(con, cur, family, mfg_id)
    series_id = get_series_id(con, cur, series, mfg_id)
    direction_id = get_direction_id(con, cur, direction)
    color_id = get_color_id(con, cur, color)

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    cavity_lock_id = get_cavity_lock_id(con, cur, cavity_lock)
    gender_id = get_gender_id(con, cur, gender)
    image_id = get_resource_id(con, cur, image)
    cad_id = get_resource_id(con, cur, cad)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if num_pins:
            description += f' {num_pins} cavity'

        if gender:
            description += f' {gender}'

        if terminal_sizes:
            t_sizes = eval(terminal_sizes)
            for t_size in t_sizes:
                description += f' {t_size}mm'

        description += ' Housing'

    cur.execute('INSERT INTO housings (part_number, description, mfg_id, family_id, series_id, '
                'color_id, min_temp_id, max_temp_id, image_id, cad_id, gender_id, '
                'direction_id, length, width, height, cavity_lock_id, sealing, '
                'rows, num_pins, terminal_sizes, centerline, compat_cpas, '
                'compat_tpas, compat_covers, compat_terminals, compat_seals, '
                'compat_housings) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 min_temp_id, max_temp_id, image_id, cad_id, gender_id,
                 direction_id, length, width, height, cavity_lock_id,
                 sealed, rows, num_pins, terminal_sizes, centerline,
                 compat_cpas, compat_tpas, compat_covers, compat_terminals,
                 compat_seals, mates_to))

    con.commit()


def add_transition_branch(con, cur, idx, transition_id, **kwargs):
    kwargs['min_dia'] = kwargs.pop('min')
    kwargs['max_dia'] = kwargs.pop('max')

    keys = sorted(list(kwargs.keys()))
    values = []

    for key in keys:
        values.append(kwargs[key])

    keys = ', '.join(keys)

    questions = ['?'] * len(values)
    questions = ', '.join(questions)

    cur.execute(f'INSERT INTO transition_branches (transition_id, idx, {keys}) VALUES (?, ?, {questions});',
                [transition_id, idx] + values)

    con.commit()


def add_transition(con, cur, part_number, description, series, material, shape,
                   max_temp, min_temp, resistances, adhesive, branch_count, branches,
                   cad, datasheet, image):

    mfg_id = 1

    series_id = get_series_id(con, cur, 'DR-25', mfg_id)
    transition_series_id = get_transition_series_id(con, cur, series)
    family_id = get_family_id(con, cur, 'RayChem', mfg_id)
    color_id = get_color_id(con, cur, 'Black')
    material_id = get_material_id(con, cur, material)
    shape_id = get_shape_id(con, cur, shape)
    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)

    protections = '\n'.join(resistances)
    protection_id = get_protection_id(con, cur, protections)

    if image:
        image_id = get_resource_id(con, cur, **image)
    else:
        image_id = 0

    if cad:
        cad_id = get_resource_id(con, cur, **cad)
    else:
        cad_id = 0

    if datasheet:
        datasheet_id = get_resource_id(con, cur, **datasheet)
    else:
        datasheet_id = 0

    adhesive_ids = str(adhesive)

    try:
        cur.execute('INSERT INTO transitions (part_number, mfg_id, description, family_id, series_id, '
                    'color_id, material_id, branch_count, shape_id, protection_id, adhesive_ids, '
                    'cad_id, datasheet_id, image_id, min_temp_id, max_temp_id, transition_series_id) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    (part_number, mfg_id, description, family_id, series_id, color_id,
                     material_id, branch_count, shape_id, protection_id, adhesive_ids,
                     cad_id, datasheet_id, image_id, min_temp_id, max_temp_id, transition_series_id))
    except:
        print('ERROR:', part_number)
        raise

    con.commit()

    transition_id = cur.lastrowid

    for i, branch in enumerate(branches):
        try:
            add_transition_branch(con, cur, i, transition_id, **branch)
        except:
            print('BRANCH ERROR:', part_number)
            continue


def add_manufacturers(con, cur):
    res = cur.execute('SELECT id FROM manufacturers WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'Internal Use DO NOT DELETE', '', '', '', ''),
        (1, 'TE', '1-800-522-6752', '', '', 'https://www.te.com/en/home.html'),
        (2, 'Bosch', '+49 304 036 94077',
         'Robert-Bosch-Platz 1\n70839 Gerlingen-Schillerhöhe\nGERMANY\n',
         'Connectors-Webshop-Hotline.PSCTS1-CO@de.bosch.com',
         'https://bosch-connectors.com/bcp/b2bshop-psconnectors/en/EUR'),
        (3, 'Aptiv', '', '', '', 'https://www.aptiv.com/en/contact'),
        (4, 'Molex', '+800-786-6539', '2222 Wellington Ct\nLisle, IL 60532, USA', '',
         'https://www.molex.com/en-us/products/connectors'),
        (5, 'EPC', '', '', '', ''),
        (6, 'Yazaki', '', '', '', ''),
        (7, 'Milspecwiring.com', '', '', '', 'https://www.milspecwiring.com'),

    )
    splash.SetText(f'Adding manufacturers to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO manufacturers (id, name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?, ?);', data)
    splash.SetText(f'Adding manufacturers to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_accessories(con, cur):
    res = cur.execute('SELECT id FROM accessories WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'None', 'No Accessories', 0),
        (1, 'S1017-1.0X50', '1" x 50\' Polyamide Adhesive, -20 – 60 °C [-4 – 140 °F], Hot Melt Tape', 1),
        (2, 'S1030', 'Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (3, 'S1030-TAPE-3/4X33FT', '3/4" x 33\' Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (4, 'S1048-TAPE-1X100-FT', '1" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (5, 'S1048-TAPE-3/4X100-FT', '3/4" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (6, 'S1125-KIT-1', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (7, 'S1125-KIT-4', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (8, 'S1125-KIT-5', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (9, 'S1125-KIT-8', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (10, 'S1125-APPLICATOR', 'Epoxy Adhesives Dispensing Gun', 1)
    )
    splash.SetText(f'Adding accessories to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO accessories (id, part_number, description, mfg_id) VALUES(?, ?, ?, ?);', data)
    splash.SetText(f'Adding accessories to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_models3d(con, cur):
    res = cur.execute('SELECT id FROM resources WHERE id=0;')
    if res.fetchall():
        return

    splash.SetText(f'Adding 3d models to db [0 | 1]...')
    cur.execute('INSERT INTO models3d (id, path) VALUES(0, "None");')
    splash.SetText(f'Adding 3d models to db [1 | 1]...')
    con.commit()


def add_resources(con, cur):
    res = cur.execute('SELECT id FROM resources WHERE id=0;')
    if res.fetchall():
        return

    splash.SetText(f'Adding resources to db [0 | 1]...')
    cur.execute('INSERT INTO resources (id, path) VALUES(0, "None");')
    splash.SetText(f'Adding temperatures to db [1 | 1]...')
    con.commit()


def add_series(con, cur):
    res = cur.execute('SELECT id FROM series WHERE id=0;')
    if res.fetchall():
        return

    splash.SetText(f'Adding series to db [0 | 1]...')
    cur.execute('INSERT INTO series (id, name) VALUES(0, "No Series");')
    splash.SetText(f'Adding series to db [1 | 1]...')
    con.commit()


def add_families(con, cur):
    res = cur.execute('SELECT id FROM families WHERE id=0;')
    if res.fetchall():
        return

    data = (0, 'No Family', 0)

    splash.SetText(f'Adding families to db [0 | {len(data)}]...')
    cur.execute('INSERT INTO families (id, name, mfg_id) VALUES(?, ?, ?);', data)
    splash.SetText(f'Adding families to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_genders(con, cur):
    res = cur.execute('SELECT id FROM genders WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Male"), (2, "Female"))

    splash.SetText(f'Adding genders to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO genders (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding genders to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_directions(con, cur):
    res = cur.execute('SELECT id FROM directions WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Left"), (2, "Right"), (3, "Straight"),
            (4, "90°"), (5, "180°"), (6, "270°"))

    splash.SetText(f'Adding directions to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO directions (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding directions to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_splice_types(con, cur):
    res = cur.execute('SELECT id FROM splice_types WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Butt"), (2, "Cable"), (3, "Closed End"),
            (4, "Parallel"), (5, "Pigtail"), (6, "Tap"),
            (7, "Thru"), (8, "Solder Sleeve"), (9, "Solder Sleeve w/Pigtail"))

    splash.SetText(f'Adding splice types to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO splice_types (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding splice types to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_temperatures(con, cur):
    res = cur.execute('SELECT id FROM temperatures WHERE id=0;')
    if res.fetchall():
        return

    splash.SetText(f'Building temperatures...')
    data = _build_temps()
    splash.SetText(f'Adding temperatures to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO temperatures (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding temperatures to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_materials(con, cur):
    res = cur.execute('SELECT * FROM materials;').fetchall()

    if res:
        return

    data = ((0, 'Unknown Material'),)

    try:
        splash.SetText(f'Adding materials to db [0 | {len(data)}]...')
        cur.executemany('INSERT INTO materials (id, name) VALUES(?, ?);', data)
        splash.SetText(f'Adding materials to db [{len(data)} | {len(data)}]...')
        con.commit()
    except:
        res = cur.execute('SELECT * FROM materials;').fetchall()
        print('ERROR:', res)
        raise


def add_platings(con, cur):
    res = cur.execute('SELECT id FROM platings WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'Unknown', 'Unknown Plating'),
        (1, 'Sn', 'Tin'),
        (2, 'Cu', 'Copper'),
        (3, 'Al', 'Aluminum'),
        (4, 'Ti', 'Titanium'),
        (5, 'Zn', 'Zinc'),
        (6, 'Au', 'Gold'),
        (7, 'Ag', 'Silver'),
        (8, 'Ni', 'Nickel'),
        (9, 'Ag/Cu', 'Silver-plated Copper'),
        (10, 'Sn/Cu', 'Tin-plated Copper'),
        (11, 'Au/Cu', 'Gold-plated Copper'),
        (12, 'Ni/Cu', 'Nickel-plated Copper'),
        (13, 'Ag/Al', 'Silver-plated Aluminum'),
        (14, 'Sn/Al', 'Tin-plated Aluminum'),
        (15, 'Au/Al', 'Gold-plated Aluminum')
    )

    splash.SetText(f'Adding platings to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO platings (id, symbol, description) VALUES(?, ?, ?);', data)
    splash.SetText(f'Adding platings to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_cavity_locks(con, cur):
    res = cur.execute('SELECT id FROM cavity_locks WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'No Lock'),
        (1, 'Cavity Lock'),
        (2, 'Locking Lance'),
        (3, 'Flex Arm'),
        (4, 'Insert Molded'),
        (5, 'Molded On'),
        (6, 'Nose Piece'),
        (7, 'Press Fit')
    )

    splash.SetText(f'Adding cavity locks to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO cavity_locks (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding cavity locks to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_colors(con, cur):
    res = cur.execute('SELECT * from colors WHERE name="Black";')
    if res.fetchall():
        return

    splash.SetText(f'Building colors...')

    data = _build_colors()

    splash.SetText(f'Adding colors to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO colors (id, name, rgb) VALUES(?, ?, ?);', data)
    splash.SetText(f'Adding colors to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_ip_fluids(con, cur):
    res = cur.execute('SELECT id FROM ip_fluids WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, '0', 'No Protection', 'No protection against ingress of water.', None),
        (1, '1', 'Dripping water', 'Dripping water (vertically falling drops) shall have no unsafe effect on the specimen when mounted upright.', open(f'{BASE_PATH}/image/ip/IPX1.png', 'rb').read()),
        (2, '2', 'Dripping water when tilted at 15°', 'Vertically dripping water shall have no harmful effect when the enclosure is tilted at an angle of 15° from its normal position.', open(f'{BASE_PATH}/image/ip/IPX2.png', 'rb').read()),
        (3, '3', 'Spraying water', 'Water falling as a spray at any angle up to 60° from the vertical shall have no harmful effect.', open(f'{BASE_PATH}/image/ip/IPX3.png', 'rb').read()),
        (4, '4', 'Splashing water', 'Water splashing against the enclosure from any direction shall have no harmful effect.', open(f'{BASE_PATH}/image/ip/IPX4.png', 'rb').read()),
        (5, '5', 'Water jets', 'Water projected by a nozzle (6.3 mm) against enclosure from any direction shall have no harmful effects.', open(f'{BASE_PATH}/image/ip/IPX5.png', 'rb').read()),
        (6, '6', 'Powerful water jets', 'Water projected in powerful jets (12.5 mm nozzle) against the enclosure from any direction shall have no harmful effects.', open(f'{BASE_PATH}/image/ip/IPX6.png', 'rb').read()),
        (7, '7', 'Immersion, up to 1 meter', 'Ingress of water in harmful quantity shall not be possible when the enclosure is immersed in water.', open(f'{BASE_PATH}/image/ip/IPX7.png', 'rb').read()),
        (8, '8', 'Immersion, 1 meter or more depth', 'The equipment is suitable for continuous immersion in water.', open(f'{BASE_PATH}/image/ip/IPX8.png', 'rb').read()),
        (9, '9', 'Powerful high-temperature water jets', 'Protected against close-range high-pressure, high-temperature spray downs.', open(f'{BASE_PATH}/image/ip/IPX9.png', 'rb').read()),
        (10, '6K', 'Powerful water jets with increased pressure', 'Water projected in powerful jets (6.3 mm nozzle) against the enclosure from any direction, under elevated pressure.', open(f'{BASE_PATH}/image/ip/IPX6K.png', 'rb').read()),
        (11, '9K', 'Steam Cleaning', 'Protection against high-pressure, high-temperature jet sprays, wash-downs or steam-cleaning procedures', open(f'{BASE_PATH}/image/ip/IPX9K.png', 'rb').read()),
        (12, 'X', 'Unknown', 'No data is available to specify a protection rating about this criterion.', None)
    )

    splash.SetText(f'Adding IP fluids to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_fluids (id, name, short_desc, description, icon_data) VALUES (?, ?, ?, ?, ?);', data)
    splash.SetText(f'Adding IP fluids to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_ip_solids(con, cur):
    res = cur.execute('SELECT id FROM ip_solids WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, '0', 'No Protection', 'No protection against contact and ingress of objects.', None),
        (1, '1', '>= 50.00mm sized objects', 'Any large surface of the body, such as the back of a hand, but no protection against deliberate contact with a body part.', open(f'{BASE_PATH}/image/ip/IP1X.png', 'rb').read()),
        (2, '2', '>= 12.50mm sized objects', 'Fingers or similar objects.', open(f'{BASE_PATH}/image/ip/IP2X.png', 'rb').read()),
        (3, '3', '>= 2.50mm sized objects', 'Tools, thick wires, etc.', open(f'{BASE_PATH}/image/ip/IP3X.png', 'rb').read()),
        (4, '4', '>= 1.00mm sized objects', 'Most wires, slender screws, large ants, etc.', open(f'{BASE_PATH}/image/ip/IP4X.png', 'rb').read()),
        (5, '5', 'Dust Protected', 'Ingress of dust is not entirely prevented.', open(f'{BASE_PATH}/image/ip/IP5X.png', 'rb').read()),
        (6, '6', 'Dust Tight', 'No ingress of dust.', open(f'{BASE_PATH}/image/ip/IP6X.png', 'rb').read()),
        (7, 'X', 'Unknown', 'No data is available to specify a protection rating about this criterion.', None)
    )

    splash.SetText(f'Adding IP solids to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_solids (id, name, short_desc, description, icon_data) VALUES (?, ?, ?, ?, ?);', data)
    splash.SetText(f'Adding IP solids to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_ip_supps(con, cur):
    res = cur.execute('SELECT id FROM ip_supps WHERE id=0;')
    if res.fetchall():
        return

    data = (
        ('D', 'Wire'),
        ('G', 'Oil resistant'),
        ('F', 'Oil resistant'),
        ('H', 'High voltage apparatus'),
        ('M', 'Motion during water test'),
        ('S', 'Stationary during water test'),
        ('W', 'Weather conditions')
    )
    splash.SetText(f'Adding IP suppliments to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_supps (name, description) VALUES (?, ?);', data)
    splash.SetText(f'Adding IP suppliments to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_ip_ratings(con, cur):
    res = cur.execute('SELECT id FROM ip_ratings WHERE id=0;')
    if res.fetchall():
        return

    add_ip_supps(con, cur)
    add_ip_solids(con, cur)
    add_ip_fluids(con, cur)

    data = (('IPOO', 0, 0), ('IPXX', 7, 12), ('IP01', 0, 1), ('IP02', 0, 2),
            ('IP03', 0, 3),
            ('IP04', 0, 4), ('IP05', 0, 5), ('IP06', 0, 6), ('IP07', 0, 7),
            ('IP08', 0, 8), ('IP09', 0, 9), ('IP06K', 0, 10), ('IP09K', 0, 11),
            ('IP0X', 0, 12), ('IP10', 1, 0), ('IP11', 1, 1), ('IP12', 1, 2),
            ('IP13', 1, 3), ('IP14', 1, 4), ('IP15', 1, 5), ('IP16', 1, 6),
            ('IP17', 1, 7), ('IP18', 1, 8), ('IP19', 1, 9), ('IP16K', 1, 10),
            ('IP19K', 1, 11), ('IP1X', 1, 12), ('IP20', 2, 0), ('IP21', 2, 1),
            ('IP22', 2, 2), ('IP23', 2, 3), ('IP24', 2, 4), ('IP25', 2, 5),
            ('IP26', 2, 6), ('IP27', 2, 7), ('IP28', 2, 8), ('IP29', 2, 9),
            ('IP26K', 2, 10), ('IP29K', 2, 11), ('IP2X', 2, 12), ('IP30', 3, 0),
            ('IP31', 3, 1), ('IP32', 3, 2), ('IP33', 3, 3), ('IP34', 3, 4),
            ('IP35', 3, 5), ('IP36', 3, 6), ('IP37', 3, 7), ('IP38', 3, 8),
            ('IP39', 3, 9), ('IP36K', 3, 10), ('IP39K', 3, 11), ('IP3X', 3, 12),
            ('IP40', 4, 0), ('IP41', 4, 1), ('IP42', 4, 2), ('IP43', 4, 3),
            ('IP44', 4, 4), ('IP45', 4, 5), ('IP46', 4, 6), ('IP47', 4, 7),
            ('IP48', 4, 8), ('IP49', 4, 9), ('IP46K', 4, 10), ('IP49K', 4, 11),
            ('IP4X', 4, 12), ('IP50', 5, 0), ('IP51', 5, 1), ('IP52', 5, 2),
            ('IP53', 5, 3), ('IP54', 5, 4), ('IP55', 5, 5), ('IP56', 5, 6),
            ('IP57', 5, 7), ('IP58', 5, 8), ('IP59', 5, 9), ('IP56K', 5, 10),
            ('IP59K', 5, 11), ('IP5X', 5, 12), ('IP60', 6, 0), ('IP61', 6, 1),
            ('IP62', 6, 2), ('IP63', 6, 3), ('IP64', 6, 4), ('IP65', 6, 5),
            ('IP66', 6, 6), ('IP67', 6, 7), ('IP68', 6, 8), ('IP69', 6, 9),
            ('IP66K', 6, 10), ('IP69K', 6, 11), ('IP6X', 6, 12), ('IPX0', 7, 0),
            ('IPX1', 7, 1), ('IPX2', 7, 2), ('IPX3', 7, 3), ('IPX4', 7, 4),
            ('IPX5', 7, 5), ('IPX6', 7, 6), ('IPX7', 7, 7), ('IPX8', 7, 8),
            ('IPX9', 7, 9), ('IPX6K', 7, 10), ('IPX9K', 7, 11))

    data = [(i,) + item for i, item in enumerate(data)]

    splash.SetText(f'Adding IP ratings to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_ratings (id, name, solid_id, fluid_id) VALUES (?, ?, ?, ?);', data)
    splash.SetText(f'Adding IP ratings to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_protections(con, cur):
    res = cur.execute('SELECT id FROM protections WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, 'No Protection'),)

    splash.SetText(f'Adding protections to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO protections (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding protections to db [{len(data)} | {len(data)}]...')
    con.commit()


def add_adhesives(con, cur):
    res = cur.execute('SELECT id FROM adhesives WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'None', 'No Adhesive', '[]'),
        (1, '225', 'Precoated latent-curing epoxy/polyamide', '[]'),
        (2, '42', 'Hot-melt/polyamide (Thermoplastic)', '[]'),
        (3, '86', 'Hot-melt,high performance (Thermoplastic)', '[]'),
        (4, 'S1006', 'Epoxy/polyamide two-part paste (Thermoset)', '[]'),
        (5, 'S1017', 'Hot-melt/polyamide (Thermoplastic)', '["S1017-1.0X50"]'),
        (6, 'S1030', 'Hot-melt/polyolefin (Thermoplastic)', '["S1030", "S1030-TAPE-3/4X33FT"]'),
        (7, 'S1048', 'Hot-melt,high performance (Thermoplastic)', '["S1048-TAPE-1X100-FT", "S1048-TAPE-3/4X100-FT"]'),
        (8, 'S1125', 'Epoxy/polyamide two-part paste (Thermoset)', '["S1125-KIT-1", "S1125-KIT-4", "S1125-KIT-5", "S1125-KIT-8","S1125-APPLICATOR"]')
    )

    splash.SetText(f'Adding adhesives to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO adhesives (id, code, description, accessory_part_nums) VALUES (?, ?, ?, ?);', data)
    splash.SetText(f'Adding adhesives to db [{len(data)} | {len(data)}]...')

    con.commit()


def add_shapes(con, cur):
    res = cur.execute('SELECT id FROM shapes WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)

    splash.SetText(f'Adding core CPA lock to db [1 | 1]...')

    cur.executemany('INSERT INTO shapes (id, name) VALUES (?, ?);', data)
    con.commit()


def add_transition_series(con, cur):
    res = cur.execute('SELECT id FROM transition_series WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)
    cur.executemany('INSERT INTO transition_series (id, name) VALUES (?, ?);', data)
    con.commit()


def cpa_locks(con, cur):
    res = cur.execute('SELECT id FROM cpa_locks WHERE id=0;')
    
    if res.fetchall():
        return
        
    add_manufacturers(con, cur)
    add_resources(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_temperatures(con, cur)
    add_colors(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core CPA lock to db [1 | 1]...')

    cur.execute('INSERT INTO cpa_locks (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'cpa_locks.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading CPA locks file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding CPA locks to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding CPA locks to db [{i} | {data_len}]...')
            add_cpa_lock(con, cur, **item)
     
        con.commit()



def tpa_locks(con, cur):

    res = cur.execute('SELECT id FROM tpa_locks WHERE id=0;')

    if res.fetchall():
        return
        
    add_manufacturers(con, cur)
    add_resources(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_temperatures(con, cur)
    add_colors(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core TPA lock to db [1 | 1]...')

    cur.execute('INSERT INTO tpa_locks (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'tpa_locks.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading TPA locks file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding TPA locks to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding TPA locks to db [{i} | {data_len}]...')
            add_tpa_lock(con, cur, **item)
     
        con.commit()



def add_seal_types(con, cur):
    res = cur.execute('SELECT id FROM seal_types WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)
    cur.executemany('INSERT INTO seal_types (id, name) VALUES (?, ?);', data)
    con.commit()


def seals(con, cur):
    res = cur.execute('SELECT id FROM seals WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_series(con, cur)
    add_colors(con, cur)
    add_temperatures(con, cur)
    add_resources(con, cur)
    add_models3d(con, cur)
    add_seal_types(con, cur)
    
    splash.SetText(f'Adding core seal to db [1 | 1]...')

    cur.execute('INSERT INTO seals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'seals.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading seals file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding seals to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding seals to db [{i} | {data_len}]...')
            add_seal(con, cur, **item)
     
        con.commit()
    


def boots(con, cur):
    res = cur.execute('SELECT id FROM boots WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_colors(con, cur)
    add_resources(con, cur)
    add_models3d(con, cur)
    
    splash.SetText(f'Adding core boot to db [1 | 1]...')

    cur.execute('INSERT INTO boots (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'boots.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading boots file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding boots to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding boots to db [{i} | {data_len}]...')
            # add_boot(con, cur, **item)
     
        con.commit()


def covers(con, cur):
    res = cur.execute('SELECT id FROM covers WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_resources(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_temperatures(con, cur)
    add_colors(con, cur)
    add_directions(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core cover to db [1 | 1]...')

    cur.execute('INSERT INTO covers (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'covers.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading covers file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding covers to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding covers to db [{i} | {data_len}]...')
            add_cover(con, cur, **item)
     
        con.commit()


def transitions(con, cur):
    res = cur.execute('SELECT id FROM transitions WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_resources(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_colors(con, cur)
    add_platings(con, cur)
    add_genders(con, cur)
    add_cavity_locks(con, cur)
    add_materials(con, cur)
    add_models3d(con, cur)
    add_transition_series(con, cur)
    add_shapes(con, cur)

    splash.SetText(f'Adding core transition to db [1 | 1]...')

    cur.execute('INSERT INTO transitions (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'transitions.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading trasitions file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding transitions to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding transitions to db [{i} | {data_len}]...')
            add_transition(con, cur, **item)
     
        con.commit()


def terminals(con, cur):
    res = cur.execute('SELECT id FROM terminals WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_resources(con, cur)
    add_series(con, cur)
    add_families(con, cur)
    add_colors(con, cur)
    add_platings(con, cur)
    add_genders(con, cur)
    add_cavity_locks(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core terminal to db [1 | 1]...')

    cur.execute('INSERT INTO terminals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'terminals.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading terminals file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
            
        data_len = len(data)

        splash.SetText(f'Adding terminals to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding terminals to db [{i} | {data_len}]...')
            add_terminal(con, cur, **item)

        con.commit()


def wires(con, cur):
    res = cur.execute('SELECT id FROM wires WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_families(con, cur)
    add_series(con, cur)
    add_colors(con, cur)
    add_temperatures(con, cur)
    add_resources(con, cur)
    add_materials(con, cur)
    add_platings(con, cur)
    
    splash.SetText(f'Adding core wire to db [1 | 1]...')
    
    cur.execute('INSERT INTO wires (id, part_number, mfg_id, description, size_mm2, '
                'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                'color_id, stripe_color_id, family_id, series_id) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 0, 'Internal Use DO NOT DELETE', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 999999, 999999, 0, 0))
    con.commit()
    
    splash.SetText(f'Building wires...')

    data = _build_wires(con, cur)
    
    data_len = len(data)
    
    splash.SetText(f'Adding wires to db [0 | {data_len}]...')

    cur.executemany('INSERT INTO wires (part_number, mfg_id, description, size_mm2, '
                    'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                    'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                    'color_id, stripe_color_id, family_id, series_id) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    data)
    
    splash.SetText(f'Adding wires to db [{data_len} | {data_len}]...')
    con.commit()

    json_path = os.path.join(DATA_PATH, 'wires.json')
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        for item in data:
            add_wire(con, cur, **item)

        con.commit()


def add_wire(con, cur, part_number, mfg, description, size_mm2, size_awg, od_mm, 
             conductor_dia_mm, weight_1km, resistance_1km, core_material, min_temp, 
             max_temp, volts, material, color, stripe_color, family, series):
    
    mfg_id = get_mfg_id(con, cur, mfg)
    core_material_id = get_material_id(con, cur, core_material)
    series_id = get_series_id(con, cur, series, mfg_id)
    family_id = get_family_id(con, cur, family, mfg_id)
    color_id = get_color_id(con, cur, color)
    stripe_color_id = get_color_id(con, cur, stripe_color if stripe_color else 'None')
    material_id = get_material_id(con, cur, material)
    min_temp_id = get_temperature_id(con, cur, min_temp)
    max_temp_id = get_temperature_id(con, cur, max_temp)
    
    cur.execute('INSERT INTO wires (part_number, mfg_id, description, size_mm2, '
                'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                'color_id, stripe_color_id, family_id, series_id) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, mfg_id, description, size_mm2, size_awg, od_mm, 
                 conductor_dia_mm, weight_1km, resistance_1km, core_material_id, 
                 min_temp_id, max_temp_id, volts, material_id, color_id, 
                 stripe_color_id, family_id, series_id))
    con.commit()


def wire_markers(con, cur):
    res = cur.execute('SELECT id FROM wire_markers WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_colors(con, cur)
    add_resources(con, cur)
    
    splash.SetText(f'Adding core wire marker to db [1 | 1]...')

    cur.execute('INSERT INTO wire_markers (id, part_number, description, mfg_id, color_id, '
                'min_diameter, max_diameter, min_awg, max_awg, image_id, datasheet_id, cad_id, '
                'length, weight, has_label) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 'Internal Use DO NOT DELETE', 0, 999999, 0, 0, 30, 30, 0, 0, 0, 0, 0, 0))
    con.commit()

    splash.SetText(f'Building wire markers...')

    data = _build_wire_markers(con, cur)

    data_len = len(data)

    splash.SetText(f'Adding wire markers to db [0 | {data_len}]')

    cur.executemany('INSERT INTO wire_markers (part_number, description, mfg_id, color_id, '
                    'min_diameter, max_diameter, min_awg, max_awg, image_id, datasheet_id, cad_id, '
                    'length, weight, has_label) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    data)
    
    splash.SetText(f'Adding wire markers to db [{data_len} | {data_len}]')
    con.commit()


def housings(con, cur):
    res = cur.execute('SELECT id FROM housings WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_families(con, cur)
    add_series(con, cur)
    add_colors(con, cur)
    add_temperatures(con, cur)
    add_resources(con, cur)
    add_genders(con, cur)
    add_directions(con, cur)
    add_cavity_locks(con, cur)
    add_ip_ratings(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core housing to db [1 | 1]...')

    cur.execute('INSERT INTO housings (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'housings.json')
    
    if os.path.exists(json_path):
        splash.SetText(f'Loading housings file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())
        
        data_len = len(data)
                
        splash.SetText(f'Adding housings to db [0 | {data_len}]')      
        for i, item in enumerate(data):
            splash.SetText(f'Adding housings to db [{i + 1} | {data_len}]')
            add_housing(con, cur, **item)

        con.commit()


def splices(con, cur):
    res = cur.execute('SELECT id FROM splices WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_families(con, cur)
    add_series(con, cur)
    add_materials(con, cur)
    add_platings(con, cur)
    add_splice_types(con, cur)
    add_colors(con, cur)
    add_temperatures(con, cur)
    add_resources(con, cur)
    add_models3d(con, cur)

    splash.SetText(f'Adding core splice to db [1 | 1]...')

    cur.execute('INSERT INTO splices (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'splices.json')
    
    if os.path.exists(json_path):
        splash.SetText(f'Loading splices file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        data_len = len(data)
        
        splash.SetText(f'Adding splices to db [0 | {data_len}]')      

        for i, item in enumerate(data):
            splash.SetText(f'Adding splices to db [{i + 1} | {data_len}]')

            # add_splice(con, cur, **item)

        con.commit()


def settings(con, cur):
    from ... import utils
    import os

    res = cur.execute('SELECT id FROM settings WHERE id=1;')

    if res.fetchall():
        return

    cur.execute(f'INSERT INTO settings (id, name, value) VALUES(1, "model_path", "\'{os.path.join(utils.get_appdata(), "models")}\'");')
    con.commit()


def bundle_covers(con, cur):
    res = cur.execute('SELECT id FROM bundle_covers WHERE id=0;')

    if res.fetchall():
        return
    
    add_manufacturers(con, cur)
    add_families(con, cur)
    add_series(con, cur)
    add_materials(con, cur)
    add_colors(con, cur)
    add_temperatures(con, cur)
    add_resources(con, cur)
    add_protections(con, cur)
    
    splash.SetText(f'Adding core bundle cover to db [1 | 1]...')

    cur.execute('INSERT INTO bundle_covers (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()
    
    json_path = os.path.join(DATA_PATH, 'bundle_covers.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading bundle covers file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        data_len = len(data)

        splash.SetText(f'Adding bundle covers to db [0 | {data_len}]')

        for i, item in enumerate(data):
            splash.SetText(f'Adding bundle covers to db [{i + 1} | {data_len}]')
            # add_bundle_cover(con, cur, **item)

        con.commit()


if __name__ == '__main__':
    import sys
    import sqlite3
    con_ = sqlite3.connect('test.db')
    cur_ = con_.cursor()

    funcs = [
        tpa_locks,
        cpa_locks,
        boots,
        terminals,
        covers,
        seals,
        transitions,
        bundle_covers,
        housings,
        splices,
        wires,
        wire_markers
    ]

    for func in funcs:
        print(func)
        sys.stdout.flush()
        try:
            func(con_, cur_)
        except:
            import traceback
            traceback.print_exc()

    cur_.close()
    con_.close()
