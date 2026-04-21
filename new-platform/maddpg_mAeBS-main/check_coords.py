import math

def check_inference_conversion():
    ref_lon = 116.355
    ref_lat = 39.962
    real_w = 6000.0
    real_h = 6000.0
    TRAIN_DIM = 6000.0
    
    SCALE_X = 111320.0 * math.cos(math.radians(ref_lat))
    SCALE_Y = 110574.0
    
    def to_model_x(lon):
        dist_x = (lon - ref_lon) * SCALE_X
        return (dist_x / real_w) * TRAIN_DIM

    def to_model_y(lat):
        dist_y = (lat - ref_lat) * SCALE_Y
        return (dist_y / real_h) * TRAIN_DIM

    test_lon = 116.35672900000000000000
    test_lat = 39.96413600000000000000
    
    mx = to_model_x(test_lon)
    my = to_model_y(test_lat)
    
    print(f"UAV1 Ref Lon: {test_lon}, Lat: {test_lat}")
    print(f"UAV1 Model X: {mx}, Model Y: {my}")

    # Check terminal user
    term_lon = 116.35720000000000000000
    term_lat = 39.96190000000000000000
    print(f"User001 Ref Lon: {term_lon}, Lat: {term_lat}")
    print(f"User001 Model X: {to_model_x(term_lon)}, Model Y: {to_model_y(term_lat)}")

if __name__ == '__main__':
    check_inference_conversion()
