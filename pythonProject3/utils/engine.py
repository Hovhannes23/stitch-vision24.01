import base64
import os
from collections import Counter

import cv2
from clustimage import Clustimage
from matplotlib import pyplot as plt
from sklearn.cluster import MiniBatchKMeans
import numpy as np
import pythonProject3.utils.preprocess as preprocess
import pythonProject3.utils.utils as utils

def detect_cells_and_clusterize(img, clusters_num, rows_num, columns_num):
    clusters_num = int(clusters_num)
    rows_num = int(rows_num)
    columns_num = int(columns_num)
    cells = detect_split_into_cells(img, rows_num, columns_num)
    labels, symbols_list = cluster_cells(cells, clusters_num)

    # раскидываем по папкам в зависимости от label, чтобы нагляднее было
    # for idx, cluster in enumerate(labels):
    #     dir_name = 'Clustered Images 60 epoch compose update/' + str(cluster)
    #     if not os.path.exists(dir_name):
    #         os.makedirs(dir_name)
    #     cv2.imwrite(dir_name + '/' + str(idx) + '.png', cells[idx])

    labels = np.array(labels)
    # for label in label_image_map.keys():
    #     img = label_image_map[label]
    #     img_no_bckg, bckg_color = detach_background(img)
    #     img_no_bckg = encode_base64(img_no_bckg)
    #     bckg_color = encode_base64(bckg_color)
    #     label_image_map[label] = (img_no_bckg, bckg_color)
    return labels, symbols_list


def response_adapter(old_response, rows_num, columns_num):
    symbols_new_resp = []

    new_response = {"rows": rows_num, "columns": columns_num}
    symbols = []
    for symbol_data in old_response["symbolsMap"]:
        new_symbol_data = {"index": symbol_data["index"], "symbol": symbol_data["symbolCode"],
                           "color": symbol_data["backgroundColor"]}
        coordinates = []
        for coordinate, index_in_matrix in np.ndenumerate(old_response["matrix"]):
            if index_in_matrix == symbol_data["index"]:
                coordinates.append({
                    "row": coordinate[0],
                    "column": coordinate[1]
                })
        new_symbol_data["coordinates"] = coordinates
        symbols.append(new_symbol_data)
    new_response["symbols"] = symbols
    return new_response

def encode_base64(input):
    input_base64 = base64.b64encode(input)
    input_base64 = input_base64.decode('ascii')
    # string_repr = base64.binascii.b2a_base64(image).decode("ascii")
    # encoded_img = np.frombuffer(base64.binascii.a2b_base64(string_repr.encode("ascii")))
    # image.save(byte_arr, format='PNG')  # convert the image to byte array
    # encoded_img = encodebytes(byte_arr.getvalue()).decode('ascii')
    return input_base64


def detect_split_into_cells(img, rows_num, columns_num):
    corner_pts = detect_corner_points(img)
    img = remove_perspective_distortion(img, corner_pts, rows_num, columns_num)
    img = 255 - img
    corner_pts = detect_corner_points(img)
    img = remove_perspective_distortion(img, corner_pts, rows_num, columns_num)
    img = 255 - img
    cells = utils.split_into_cells(img, rows_num, columns_num)
    return cells

def detect_and_get_cells_for_sup(img, corner_pts, rows_num, columns_num, cluster_num):
    img = remove_perspective_distortion(img, corner_pts, rows_num, columns_num)
    cells = utils.split_into_cells(img, rows_num, columns_num)
    labels, symbols_list = cluster_cells(cells, cluster_num)

    return labels, symbols_list
def detect_corner_points(img):
    imgBigContour = img.copy()
    # showImage(img)
    imgThresholdBinInvOtsu = utils.preProcess(img)
    # showImage(imgThreshold)

    # Find contours
    imgContours = img.copy()
    contours, hierarchy = cv2.findContours(imgThresholdBinInvOtsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(imgContours, contours, -1, (255, 0, 0), 10)

    # utils.showImage(imgContours)
    # Biggest contour
    biggest, maxArea = utils.findBiggestContour(contours)
    if biggest.size != 0:
        biggest = utils.reorder(biggest)
        cv2.drawContours(imgBigContour, biggest, -1, (255, 0, 0), 10)
        # utils.showImage(imgBigContour)

    return biggest

def remove_perspective_distortion(img, corner_pts, rows, columns):
    # detect rectangle for perspective distortion
    rectangle_pts = utils.get_rectangle_points(corner_pts)
    w = rectangle_pts[3, 0]
    h = rectangle_pts[3, 1]

    if rows or columns !=0:
        w = utils.change_num(w, columns)
        h = utils.change_num(h, rows)
    w = int(w)
    h = int(h)
    pts1 = np.float32(corner_pts)
    pts2 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    img = cv2.warpPerspective(img, matrix, (w, h))
    # utils.showImage(img)

    return img

def cluster_cells(cells, cluster_count):
    cluster_count = int(cluster_count)

    # временный код для добавления помеченных изображений
    cells = upload_images_to_cells(cells, for_blank=True)
    result, cl = clusterize_images(cells, 2)
    # result, cl = clusterize_images(cells, cluster_count)

    labels_all = result["labels"]
    save_images(cells, labels_all, 'with_blank')

    # последним у нас был помеченный пустой символ, находим его label
    label_of_blank = labels_all[-1]

    # удаляем последний label, так как он помеченный
    labels_all = labels_all[:-1]
    cells = cells[:-1]

    # отделяем изображения, на которых есть символы (которые не blank)
    cells_without_blank = []
    for idx, label in enumerate(labels_all):
        if label != label_of_blank:
            cells_without_blank.append(cells[idx])

    # добавляем non blank помеченные изображения
    cells_without_blank = upload_images_to_cells(cells_without_blank, for_blank=False)

    result, cl = clusterize_images(cells_without_blank, cluster_count - 1)

    labels_without_blank = result["labels"]
    save_images(cells_without_blank, labels_without_blank, 'no_blank')


    label_elka = labels_without_blank[-5]
    label_flower = labels_without_blank[-4]
    label_kolos = labels_without_blank[-3]
    label_square = labels_without_blank[-2]
    label_sun = labels_without_blank[-1]

    # удаляем последние 5 элементов, так как они помеченные
    labels_without_blank = labels_without_blank[:-5]

    labels, new_label_blank = change_labels(labels_all, labels_without_blank, label_of_blank)

    symbols_list = []
    symbol_data0 = {}
    label_count = Counter(labels)

    symbol_data0["index"] = int(-1)
    symbol_data0["symbolCode"] = ""
    symbol_data0["backgroundColor"] = "#FFFFFF"
    symbol_data0["count"] = label_count[-1]
    symbols_list.append(symbol_data0)

    symbol_data1 = {}
    symbol_data1["index"] = int(label_elka)
    symbol_data1["symbolCode"] = "aa"
    symbol_data1["backgroundColor"] = detach_background(cells_without_blank[-5])[1]
    symbol_data1["count"] = label_count[label_elka]
    symbols_list.append(symbol_data1)

    symbol_data2 = {}
    symbol_data2["index"] = int(label_flower)
    symbol_data2["symbolCode"] = "cd"
    symbol_data2["backgroundColor"] = detach_background(cells_without_blank[-4])[1]
    symbol_data2["count"] = label_count[label_flower]
    symbols_list.append(symbol_data2)

    symbol_data3 = {}
    symbol_data3["index"] = int(label_kolos)
    symbol_data3["symbolCode"] = "41"
    symbol_data3["backgroundColor"] = detach_background(cells_without_blank[-3])[1]
    symbol_data3["count"] = label_count[label_kolos]
    symbols_list.append(symbol_data3)

    symbol_data4 = {}
    symbol_data4["index"] = int(label_square)
    symbol_data4["symbolCode"] = "44"
    symbol_data4["backgroundColor"] = detach_background(cells_without_blank[-2])[1]
    symbol_data4["count"] = label_count[label_square]
    symbols_list.append(symbol_data4)

    symbol_data5 = {}
    symbol_data5["index"] = int(label_sun)
    symbol_data5["symbolCode"] = "51"
    symbol_data5["backgroundColor"] = detach_background(cells_without_blank[-1])[1]
    symbol_data5["count"] = label_count[label_sun]
    symbols_list.append(symbol_data5)

    # return labels, symbols_list
    # конец временного кода

    # save_images(cells, labels_all)

    # cl.scatter(zoom=4)
    # cl.dendogram()
    # cl.pca.plot()
    # cl.pca.scatter(legend=False, label=False)
    # cl.clusteval.plot()
    return labels, symbols_list


def save_images(cells, labels, dir_name):
    for idx, cluster in enumerate(labels):
        folder_name = dir_name + '/' + str(cluster)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        cv2.imwrite(folder_name + '/' + str(idx) + '.png', cells[idx])

# временный метод для добавления помеченных изображений к изображениям ячеек
# for_blank = True, если добавляем к cells изображение пустой ячейки (blank.jpg)
# for_blank = False, если добавляем изображения непустых ячеек
def upload_images_to_cells(cells, for_blank):
    folder = "pythonProject3/resources/chashkaSymbols"
    images = []
    filenames = os.listdir(folder)

    if for_blank:
        filenames = ["blank.jpg"]
    else:
        filenames.remove("blank.jpg")

    filenames = sorted(filenames)
    for filename in filenames:
        img = cv2.imread(os.path.join(folder, filename))
        if img is not None:
            images.append(img)
    cells = list(cells)
    cells.extend(images)
    return cells


# labels_all - матрица, в которой label-ы разделены на blank и non blank
# labels_without_blank - матрица, в которой все non blank label-ы из labels_all кластеризированы
# Метод заменяет non blank label-ы из labels_all на их кластеризированные значения (так как в labels_all они все лежат
# под одним label-ом)
def change_labels(labels_all, labels_without_blank, label_of_blank):
    # new_label_blank = np.max(labels_without_blank) + 1
    new_label_blank = -1
    new_labels_matrix = []
    idx_without_blank = 0
    for label in labels_all:
        if label == label_of_blank:
            label = new_label_blank
        else:
            label = labels_without_blank[idx_without_blank]
            idx_without_blank += 1
        new_labels_matrix.append(label)

    return new_labels_matrix, new_label_blank

def clusterize_images(images, cluster_count):
    sobel_images = []
    for img in images:
        img = preprocess.resize_and_RGB(img)
        img = preprocess.blur_and_Sobel(img)
        plt.show()
        img = img.flatten()
        sobel_images.append(img)

    sobel_images = np.array(sobel_images)
    cl = Clustimage(method='pca', params_pca={'n_components': cluster_count * 4}, dim=(128, 128))
    # cl = Clustimage(method='hog', params_hog={'orientations': 8, 'pixels_per_cell': (8, 8), 'cells_per_block': (1, 1)}, dim=(128, 128))
    result = cl.fit_transform(sobel_images, min_clust=cluster_count, max_clust=cluster_count + 1)
    # cl.scatter(zoom=4)
    # cl.dendogram()
    # cl.pca.plot()
    # cl.pca.scatter(legend=False, label=False)
    # cl.clusteval.plot()
    return result, cl


def detach_background(image):
    # utils.showImage(image)
    (h, w) = image.shape[:2]
    # convert the image from the RGB color space to the L*a*b*
    # color space -- since we will be clustering using k-means
    # which is based on the euclidean distance, we'll use the
    # L*a*b* color space where the euclidean distance implies
    # perceptual meaning
    image = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    # reshape the image into a feature vector so that k-means
    # can be applied
    image = image.reshape((image.shape[0] * image.shape[1], 3))
    # apply k-means using the specified number of clusters and
    # then create the quantized image based on the predictions
    clt = MiniBatchKMeans(n_clusters=2)
    labels = clt.fit_predict(image)
    quant = clt.cluster_centers_.astype("uint8")[labels]

    # to RGB
    quant = quant.reshape((h, w, 3))
    image = image.reshape((h, w, 3))
    quant = cv2.cvtColor(quant, cv2.COLOR_LAB2RGB)
    image = cv2.cvtColor(image, cv2.COLOR_LAB2RGB)

    # find most frequent color
    image = image.reshape((image.shape[0] * image.shape[1], 3))
    quant = quant.reshape((quant.shape[0] * quant.shape[1], 3))
    colors, counts = np.unique(quant, axis=0, return_counts=True)
    ind = np.argmax(counts)
    most_frequent_color = colors[ind]

    quant = quant.reshape((h, w, 3))
    image = image.reshape((h, w, 3))

    # delete background color
    mask_without_bckgrd = cv2.inRange(quant, most_frequent_color, most_frequent_color)
    # mask_without_bckgrd = cv2.cvtColor(mask_without_bckgrd, cv2.COLOR_GRAY2RGB)
    mask_without_bckgrd = mask_without_bckgrd - 255

    image_without_bckgrd = cv2.bitwise_and(image, image, mask=mask_without_bckgrd)
    most_frequent_color = RGB_to_HEX(most_frequent_color)

    return image_without_bckgrd, most_frequent_color


def RGB_to_HEX(rgb):
    rgb = (rgb[0], rgb[1], rgb[2])
    return '#' + '%02x%02x%02x' % rgb

def order_points(pts):
    pts = pts.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="int32")
    # у верхней левой точки будет наименьшая сумма
    # у нижней правой точки будет наибольшая сумма
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # высчитываем y-х для каждой точки.
    # у верхней правой точки результат будет наименьшим
    # у нижней левой точки результат будет наибольшим
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect