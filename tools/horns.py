"""The same part profile is used for image fitting and mesh generation."""
def horn_profile(span, rise):
    sections = [
        (.30,-.10,4.35,.170,.160), (.46,-.095,4.365,.166,.159),
        (.66,-.077,4.35,.144,.145), (.84,-.081,4.40,.125,.13),
        (.97,-.116,4.52,.098,.11), (1.005,-.16,4.665,.076,.080),
        (.964,-.215,4.79,.043,.045), (.858,-.263,4.89,.003,.003),
    ]
    return [(.30+(x-.30)*span, y, 4.35+(z-4.35)*rise, w, d)
            for x,y,z,w,d in sections]
